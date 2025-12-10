"""
AI Service - LLM integration for chat and recommendations
"""
import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from config import LLMConfig, KNOWLEDGE_BASE
from database import get_knowledge_base, save_knowledge_rating, get_flagged_knowledge_entries
from database import get_all_dishes, get_user_by_id, get_orders_by_customer, get_all_users
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

def call_gemini(prompt: str) -> Optional[str]:
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{LLMConfig.GEMINI_MODEL}:generateContent?key={LLMConfig.GEMINI_API_KEY}"
        )

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }

        response = requests.post(
            url,
            json=payload,
            timeout=LLMConfig.TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        print("Gemini error:", response.text)
        return None

    except Exception as e:
        print("Gemini exception:", e)
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
        url = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"{LLMConfig.GEMINI_MODEL}:generateContent?key={LLMConfig.GEMINI_API_KEY}"
        )



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

def build_menu_context(user_id: Optional[str] = None) -> str:
    """
    Build comprehensive menu and restaurant context for AI
    Returns: Formatted string with all menu information
    """
    dishes = get_all_dishes()
    users = get_all_users()
    chefs = {u.id: u.username for u in users if u.role == 'chef'}
    
    # Filter dishes based on user VIP status
    if user_id:
        user = get_user_by_id(user_id)
        if user and user.role != 'vip':
            dishes = [d for d in dishes if not d.vip_only]
    
    # Group dishes by category
    menu_by_category = {}
    for dish in dishes:
        if dish.available:  # Only include available dishes
            category = dish.category
            if category not in menu_by_category:
                menu_by_category[category] = []
            
            chef_name = chefs.get(dish.chef_id, 'Unknown Chef')
            rating_str = f"{dish.rating:.1f}⭐" if dish.rating > 0 else "No ratings yet"
            vip_note = " (VIP Only)" if dish.vip_only else ""
            flavor_tags_str = ", ".join(dish.flavor_tags) if dish.flavor_tags else "No flavor tags"
            
            dish_info = f"- {dish.name} (${dish.price:.2f}){vip_note}\n"
            dish_info += f"  Description: {dish.description}\n"
            dish_info += f"  Chef: {chef_name} | Rating: {rating_str} | Category: {category}\n"
            dish_info += f"  Flavor tags: {flavor_tags_str}\n"
            dish_info += f"  Orders: {dish.orders_count} | ID: {dish.id}\n"
            
            menu_by_category[category].append(dish_info)
    
    # Build menu context string
    menu_context = "\n=== CURRENT MENU ===\n\n"
    
    if not menu_by_category:
        menu_context += "No dishes available at the moment.\n"
    else:
        for category in ['appetizers', 'main', 'desserts', 'beverages']:
            if category in menu_by_category:
                menu_context += f"\n{category.upper()}:\n"
                menu_context += "\n".join(menu_by_category[category])
                menu_context += "\n"
    
    # Add summary statistics
    available_dishes = [d for d in dishes if d.available]
    total_dishes = len(available_dishes)
    
    menu_context += f"\n=== MENU SUMMARY ===\n"
    menu_context += f"Total available dishes: {total_dishes}\n"
    
    if available_dishes:
        rated_dishes = [d for d in available_dishes if d.rating > 0]
        if rated_dishes:
            avg_rating = sum(d.rating for d in rated_dishes) / len(rated_dishes)
            menu_context += f"Average dish rating: {avg_rating:.1f} stars\n"
        
        prices = [d.price for d in available_dishes]
        if prices:
            menu_context += f"Price range: ${min(prices):.2f} - ${max(prices):.2f}\n"
    
    return menu_context

def get_ai_response(message: str, user_id: Optional[str] = None) -> Dict:
    """
    Get AI response to user message
    Returns: {'success': bool, 'reply': str, 'source': str}
    """
    
    # First, try knowledge base
    kb_result = search_knowledge_base(message)
    if kb_result:
        return {
            'success': True,
            'reply': kb_result['answer'],
            'source': 'knowledge_base',
            'entry_id': kb_result['entry_id']
        }
    
    # Build comprehensive context for LLM
    context = "You are a helpful customer service assistant for a restaurant. "
    context += "Answer questions about the menu, ordering, delivery, and general restaurant information. "
    context += "Be friendly and concise. Use the menu information provided to answer specific questions about dishes, prices, and availability.\n\n"
    
    # Add user context
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            context += f"Customer Information:\n"
            context += f"- Username: {user.username}\n"
            context += f"- Role: {user.role}\n"
            if user.role == 'vip':
                context += f"- VIP Benefits: 5% discount, free delivery (1 per 3 orders), access to special dishes\n"
            context += "\n"
    
    # Add full menu information
    menu_context = build_menu_context(user_id)
    context += menu_context
    
    # Add restaurant information
    context += "\n=== RESTAURANT INFORMATION ===\n"
    context += "- Hours: Monday through Sunday, 11:00 AM to 10:00 PM\n"
    context += "- Payment: Deposit-based system (users maintain account balance)\n"
    context += "- Delivery: Available (VIP members get 1 free delivery per 3 orders)\n"
    context += "- VIP Membership: Available after spending $100 or making 3 orders without complaints\n"
    context += "- VIP Benefits: 5% discount, free delivery benefits, access to special dishes\n"
    
    prompt = f"{context}\n\nCustomer Question: {message}\n\nAssistant Response:"
    
    # Try LLM
    reply = None
    if LLMConfig.PROVIDER == 'ollama':
        reply = call_ollama(prompt)
    elif LLMConfig.PROVIDER == 'huggingface' and LLMConfig.HUGGINGFACE_TOKEN:
        reply = call_huggingface(prompt)
    elif LLMConfig.PROVIDER == 'gemini':
        reply = call_gemini(prompt)
    
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
        
        # Flavor profile matching
        if dish.flavor_tags:
            match_score = calculate_flavor_match(user.flavor_profile, dish.flavor_tags)
        
        # Boost based on order history (if user ordered similar dishes)
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
        
        dish_dict = dish.to_dict()
        dish_dict['match_score'] = round(match_score, 1)
        recommendations.append(dish_dict)
    
    # Sort by match score and return top recommendations
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    return recommendations[:limit]

def get_flavor_preferences_from_orders(user_id: str) -> Optional[Dict]:
    """
    Calculate flavor preferences from user's order history
    Returns: Dictionary with flavor tags as keys and percentages as values
    """
    user_orders = get_orders_by_customer(user_id)
    if not user_orders:
        return None
    
    dishes = get_all_dishes()
    dishes_dict = {d.id: d for d in dishes}
    
    # Count occurrences of each flavor tag across all ordered dishes
    flavor_counts = {}
    total_dishes = 0
    
    for order in user_orders:
        for item in order.items:
            dish_id = item.get('dish_id')
            dish = dishes_dict.get(dish_id)
            
            if dish and dish.flavor_tags:
                total_dishes += 1
                for tag in dish.flavor_tags:
                    flavor_counts[tag] = flavor_counts.get(tag, 0) + 1
    
    if total_dishes == 0:
        return None
    
    # Calculate percentages (how often each flavor appears)
    flavor_preferences = {}
    for tag, count in flavor_counts.items():
        # Calculate percentage: (count / total_dishes) * 100
        percentage = (count / total_dishes) * 100
        flavor_preferences[tag] = round(percentage, 1)
    
    return flavor_preferences if flavor_preferences else None

def get_flavor_profile_analysis(user_id: str) -> Dict:
    """
    Analyze user's flavor profile and provide insights
    """
    user = get_user_by_id(user_id)
    if not user:
        return {}
    
    profile = user.flavor_profile
    
    # Ensure profile is a dict and not empty
    if not profile or not isinstance(profile, dict) or len(profile) == 0:
        return {
            'dominant_flavor': None,
            'profile': profile or {},
            'recommendations': []
        }
    
    # Find dominant flavor (highest value)
    # Only consider flavors with value > 0
    valid_items = [(tag, value) for tag, value in profile.items() if value > 0]
    
    if not valid_items:
        # All values are 0, no dominant flavor
        max_tag = None
    else:
        max_tag = max(valid_items, key=lambda x: x[1])
    
    analysis = {
        'dominant_flavor': max_tag[0] if max_tag else None,
        'profile': profile,
        'recommendations': []
    }
    
    # Get recommendations based on dominant flavor
    if max_tag and max_tag[1] > 0:
        dishes = get_all_dishes()
        matching_dishes = [d for d in dishes if max_tag[0] in d.flavor_tags and d.available]
        analysis['recommendations'] = [d.to_dict() for d in matching_dishes[:5]]
    
    return analysis
