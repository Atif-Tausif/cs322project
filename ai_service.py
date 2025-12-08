"""
AI Service - LLM integration for chat and recommendations
"""
import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from config import LLMConfig, KNOWLEDGE_BASE
from database import get_knowledge_base, save_knowledge_rating, get_flagged_knowledge_entries
from database import get_all_dishes, get_user_by_id, get_orders_by_customer
from utils import calculate_flavor_match

def search_knowledge_base(query: str) -> Optional[Dict]:
    """
    Search knowledge base for matching answer
    Returns: {'answer': str, 'entry_id': str} or None
    """
    query_lower = query.lower()
    
    # Get all knowledge base entries (default + user-contributed)
    entries = get_knowledge_base()
    
    for entry in entries:
        # Skip unapproved user entries
        if entry.get('author_id') and not entry.get('approved', False):
            continue
        
        # Check if query matches question or tags
        question_match = entry['question'].lower() in query_lower or query_lower in entry['question'].lower()
        tag_match = any(tag.lower() in query_lower for tag in entry.get('tags', []))
        
        if question_match or tag_match:
            entry_id = entry.get('id', f"kb_{hash(entry.get('question', ''))}")
            return {
                'answer': entry['answer'],
                'entry_id': entry_id,
                'source': 'knowledge_base'
            }
    
    return None

def call_ollama(prompt: str) -> Optional[str]:
    """Call Ollama API"""
    try:
        url = f"{LLMConfig.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": LLMConfig.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=LLMConfig.TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def call_huggingface(prompt: str) -> Optional[str]:
    """Call HuggingFace API"""
    try:
        url = f"{LLMConfig.HUGGINGFACE_API_URL}/{LLMConfig.HUGGINGFACE_MODEL}"


        headers = {
            "Authorization": f"Bearer {LLMConfig.HUGGINGFACE_TOKEN}"
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": 200,
                "temperature": 0.7
            }
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=LLMConfig.TIMEOUT
        )
        print("HF STATUS:", response.status_code)
        print("HF RAW RESPONSE:", response.text[:500])

        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '')
            return str(result)
        return None
    except Exception as e:
        print(f"HuggingFace error: {e}")
        return None

def get_ai_response(message: str, user_id: Optional[str] = None) -> Dict:
    """
    Get AI response to user message
    Returns: {'success': bool, 'reply': str, 'source': str}
    """

    print("DEBUG LLM Provider:", LLMConfig.PROVIDER)
    print("DEBUG HF Token Exists:", bool(LLMConfig.HUGGINGFACE_TOKEN))
    print("DEBUG Model:", LLMConfig.HUGGINGFACE_MODEL)



    # First, try knowledge base
    kb_result = search_knowledge_base(message)
    if kb_result:
        return {
            'success': True,
            'reply': kb_result['answer'],
            'source': 'knowledge_base',
            'entry_id': kb_result['entry_id']
        }
    
    # Build context for LLM
    context = "You are a helpful customer service assistant for a restaurant. "
    context += "Answer questions about the menu, ordering, delivery, and general restaurant information. "
    context += "Be friendly and concise. "
    
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            context += f"The customer is {user.username}. "
            if user.role == 'vip':
                context += "They are a VIP member. "
    
    prompt = f"{context}\n\nCustomer: {message}\nAssistant:"
    
    # Try LLM
    reply = None
    if LLMConfig.PROVIDER == 'ollama':
        reply = call_ollama(prompt)
    elif LLMConfig.PROVIDER == 'huggingface' and LLMConfig.HUGGINGFACE_TOKEN:
        reply = call_huggingface(prompt)
    
    if reply:
        return {
            'success': True,
            'reply': reply.strip(),
            'source': 'llm'
        }
    
    # Fallback response
    return {
        'success': True,
        'reply': "I'm sorry, I'm having trouble processing your request right now. Please try rephrasing your question or contact our support team.",
        'source': 'fallback'
    }

def get_personalized_recommendations(user_id: str, limit: int = 6) -> List[Dict]:
    """
    Get personalized dish recommendations for a user
    Returns: List of dish dictionaries with match_score
    """
    user = get_user_by_id(user_id)
    if not user:
        return []
    
    dishes = get_all_dishes()
    user_orders = get_orders_by_customer(user_id)
    
    # Filter dishes based on VIP status
    if user.role != 'vip':
        dishes = [d for d in dishes if not d.vip_only]
    
    # Calculate match scores
    recommendations = []
    for dish in dishes:
        if not dish.available:
            continue
        
        match_score = 0.0
        
        # Flavor profile matching - use preferences from order history
        if dish.flavor_tags:
            from ai_service import get_flavor_preferences_from_orders
            flavor_preferences = get_flavor_preferences_from_orders(user_id)
            match_score = calculate_flavor_match(flavor_preferences, dish.flavor_tags)
        
        # Boost based on order history (if user ordered similar dishes)
        # Note: These boosts are applied as percentage points, but we cap at 100%
        if user_orders:
            ordered_dish_ids = set()
            for order in user_orders:
                for item in order.items:
                    ordered_dish_ids.add(item.get('dish_id'))
            
            # Boost if dish is from same chef as previously ordered dishes
            ordered_dishes = [d for d in dishes if d.id in ordered_dish_ids]
            if ordered_dishes:
                same_chef_dishes = [d for d in ordered_dishes if d.chef_id == dish.chef_id]
                if same_chef_dishes:
                    match_score += 10
        
        # Boost highly rated dishes
        if dish.rating >= 4.0:
            match_score += 5
        
        # Cap match score at 100% (since it's a percentage)
        match_score = min(100.0, match_score)
        
        dish_dict = dish.to_dict()
        dish_dict['match_score'] = round(match_score, 1)
        recommendations.append(dish_dict)
    
    # Sort by match score and return top recommendations
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    return recommendations[:limit]

def get_flavor_preferences_from_orders(user_id: str) -> Dict:
    """
    Calculate flavor preferences based on order history (percentage of orders with each flavor)
    Returns a dictionary with flavor percentages
    """
    from database import get_orders_by_customer
    from database import get_all_dishes
    
    orders = get_orders_by_customer(user_id)
    if not orders:
        return {'spicy': 0, 'sweet': 0, 'savory': 0, 'tangy': 0}
    
    dishes = {d.id: d for d in get_all_dishes()}
    flavor_counts = {'spicy': 0, 'sweet': 0, 'savory': 0, 'tangy': 0}
    total_items = 0
    
    for order in orders:
        for item in order.items:
            dish_id = item.get('dish_id')
            dish = dishes.get(dish_id)
            if dish and dish.flavor_tags:
                total_items += 1
                for flavor in dish.flavor_tags:
                    if flavor in flavor_counts:
                        flavor_counts[flavor] += 1
    
    # Calculate percentages
    if total_items > 0:
        flavor_percentages = {flavor: (count / total_items * 100) for flavor, count in flavor_counts.items()}
    else:
        flavor_percentages = {flavor: 0 for flavor in flavor_counts.keys()}
    
    return flavor_percentages

def get_flavor_profile_analysis(user_id: str) -> Dict:
    """
    Analyze user's flavor profile and provide insights
    """
    user = get_user_by_id(user_id)
    if not user:
        return {}
    
    profile = user.flavor_profile
    max_tag = max(profile.items(), key=lambda x: x[1]) if profile else None
    
    analysis = {
        'dominant_flavor': max_tag[0] if max_tag and max_tag[1] > 0 else None,
        'profile': profile,
        'recommendations': []
    }
    
    if max_tag:
        dishes = get_all_dishes()
        matching_dishes = [d for d in dishes if max_tag[0] in d.flavor_tags and d.available]
        analysis['recommendations'] = [d.to_dict() for d in matching_dishes[:5]]
    
    return analysis
