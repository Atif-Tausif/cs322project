"""
AI Service - LLM integration for chat and recommendations
"""
import os
import requests
import json
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from config import LLMConfig
from database import get_knowledge_base, save_knowledge_rating, get_flagged_knowledge_entries
from database import get_all_dishes, get_user_by_id, get_orders_by_customer, get_all_users
from utils import calculate_flavor_match

if TYPE_CHECKING:
    from models import Dish

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
    
    # Get flavor preferences from order history (same as menu)
    flavor_preferences = get_flavor_preferences_from_orders(user_id)
    
    # Calculate match scores
    recommendations = []
    for dish in dishes:
        if not dish.available:
            continue
        
        match_score = 0.0
        
        # Flavor profile matching (same calculation as menu)
        if flavor_preferences and dish.flavor_tags:
            match_score = calculate_flavor_match(flavor_preferences, dish.flavor_tags)
        
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

def estimate_nutritional_info(dish_name: str, dish_description: str, category: str = 'main') -> Optional[Dict]:
    """
    Estimate nutritional information for a dish using AI (Gemini)
    Returns: Dictionary with nutritional information or None if failed
    Format: {
        'calories': int,
        'protein': float (grams),
        'carbs': float (grams),
        'fat': float (grams),
        'fiber': float (grams),
        'allergens': List[str],
        'dietary_tags': List[str]  # e.g., 'vegetarian', 'gluten-free', 'vegan'
    }
    """
    try:
        prompt = f"""Analyze the following dish and estimate its nutritional information.
Dish Name: {dish_name}
Description: {dish_description}
Category: {category}

Please provide nutritional estimates in JSON format. Be realistic and consider typical serving sizes for this type of dish.
Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
    "calories": <integer estimate>,
    "protein": <float grams>,
    "carbs": <float grams>,
    "fat": <float grams>,
    "fiber": <float grams>,
    "allergens": [<list of potential allergens like "dairy", "nuts", "gluten", "eggs", "seafood", "soy">],
    "dietary_tags": [<list of dietary tags like "vegetarian", "vegan", "gluten-free", "keto-friendly", "high-protein", "low-carb">]
}}

Examples of allergens: dairy, nuts, gluten, eggs, seafood, soy, shellfish
Examples of dietary tags: vegetarian, vegan, gluten-free, keto-friendly, high-protein, low-carb, low-fat, low-calorie

Only include allergens and dietary tags if you are reasonably confident based on the description.
If unsure about allergens or dietary tags, use empty arrays.
Return ONLY the JSON object, nothing else."""

        response = call_gemini(prompt)
        
        if not response:
            return None
        
        # Clean the response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON
        nutrition_data = json.loads(response)
        
        # Validate required fields
        required_fields = ['calories', 'protein', 'carbs', 'fat', 'fiber']
        if not all(field in nutrition_data for field in required_fields):
            return None
        
        # Ensure numeric fields are valid
        nutrition_data['calories'] = int(nutrition_data.get('calories', 0))
        nutrition_data['protein'] = float(nutrition_data.get('protein', 0))
        nutrition_data['carbs'] = float(nutrition_data.get('carbs', 0))
        nutrition_data['fat'] = float(nutrition_data.get('fat', 0))
        nutrition_data['fiber'] = float(nutrition_data.get('fiber', 0))
        
        # Ensure lists exist
        nutrition_data['allergens'] = nutrition_data.get('allergens', [])
        nutrition_data['dietary_tags'] = nutrition_data.get('dietary_tags', [])
        
        return nutrition_data
        
    except Exception as e:
        print(f"Error estimating nutritional info: {e}")
        return None

def generate_meal_plan(
    preferences: Dict,
    available_dishes: List['Dish'],
    user_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Generate a complete meal plan based on user preferences and nutritional requirements
    
    Args:
        preferences: Dict with keys:
            - meal_types: List[str] - ['appetizer', 'main', 'dessert', 'beverage']
            - allergies: List[str] - ['dairy', 'nuts', 'gluten', etc.]
            - nutritional_goals: Dict - {'high_protein': bool, 'low_calorie': bool, 'high_fiber': bool, etc.}
            - max_calories: Optional[int]
            - min_protein: Optional[float]
            - cuisine_preference: Optional[str]
            - dietary_tags: List[str] - ['vegetarian', 'vegan', 'keto-friendly', etc.]
        available_dishes: List of all available dishes
        user_id: Optional user ID for personalized recommendations
    
    Returns:
        Dict with meal plan containing dishes and total nutrition info
    """
    try:
        from database import save_dish
        
        # Filter dishes based on allergies and dietary requirements
        filtered_dishes = []
        for dish in available_dishes:
            if not dish.available:
                continue
            
            # Filter VIP-only dishes
            if user_id:
                user = get_user_by_id(user_id)
                if dish.vip_only and (not user or user.role != 'vip'):
                    continue
            elif dish.vip_only:
                continue
            
            # Get nutritional info (calculate if not cached)
            if not dish.nutritional_info:
                nutrition = estimate_nutritional_info(dish.name, dish.description, dish.category)
                if nutrition:
                    dish.nutritional_info = nutrition
                    save_dish(dish)
            
            # Check allergies
            if dish.nutritional_info:
                allergens = dish.nutritional_info.get('allergens', [])
                user_allergies = [a.lower() for a in preferences.get('allergies', [])]
                if any(allergen.lower() in user_allergies for allergen in allergens):
                    continue
            
            # Check dietary tags
            if dish.nutritional_info:
                dietary_tags = [t.lower() for t in dish.nutritional_info.get('dietary_tags', [])]
                required_tags = [t.lower() for t in preferences.get('dietary_tags', [])]
                if required_tags and not any(tag in dietary_tags for tag in required_tags):
                    continue
            
            filtered_dishes.append(dish)
        
        if not filtered_dishes:
            return None
        
        # Build context for AI
        menu_context = "\n=== AVAILABLE DISHES ===\n\n"
        dishes_by_category = {}
        for dish in filtered_dishes:
            category = dish.category
            if category not in dishes_by_category:
                dishes_by_category[category] = []
            
            nutrition_str = ""
            if dish.nutritional_info:
                n = dish.nutritional_info
                nutrition_str = f" | Calories: {n.get('calories', 'N/A')}, Protein: {n.get('protein', 0):.1f}g"
                if n.get('allergens'):
                    nutrition_str += f" | Allergens: {', '.join(n.get('allergens', []))}"
                if n.get('dietary_tags'):
                    nutrition_str += f" | Dietary: {', '.join(n.get('dietary_tags', []))}"
            
            menu_context += f"- {dish.name} (${dish.price:.2f}) - {dish.category}{nutrition_str}\n"
            menu_context += f"  Description: {dish.description}\n"
            menu_context += f"  ID: {dish.id}\n\n"
        
        # Build preferences string
        pref_str = "Meal Types Requested: " + ", ".join(preferences.get('meal_types', ['main'])) + "\n"
        
        if preferences.get('allergies'):
            pref_str += f"Allergies to Avoid: {', '.join(preferences.get('allergies', []))}\n"
        
        if preferences.get('dietary_tags'):
            pref_str += f"Dietary Requirements: {', '.join(preferences.get('dietary_tags', []))}\n"
        
        nutritional_goals = preferences.get('nutritional_goals', {})
        if nutritional_goals.get('high_protein'):
            pref_str += "Goal: High Protein\n"
        if nutritional_goals.get('low_calorie'):
            pref_str += "Goal: Low Calorie\n"
        if nutritional_goals.get('high_fiber'):
            pref_str += "Goal: High Fiber\n"
        
        if preferences.get('max_calories'):
            pref_str += f"Max Total Calories: {preferences.get('max_calories')}\n"
        
        if preferences.get('min_protein'):
            pref_str += f"Min Total Protein: {preferences.get('min_protein')}g\n"
        
        # Create AI prompt
        prompt = f"""You are a nutritionist creating a balanced meal plan from the available dishes.

{pref_str}

{menu_context}

Create a meal plan that matches these preferences. Select dishes from different categories to create a complete meal.
Return ONLY valid JSON (no markdown, no explanation) in this exact format:
{{
    "meal_plan": {{
        "appetizer": {{"dish_id": "<id>", "name": "<name>", "reason": "<why this was chosen>"}},
        "main": {{"dish_id": "<id>", "name": "<name>", "reason": "<why this was chosen>"}},
        "dessert": {{"dish_id": "<id>", "name": "<name>", "reason": "<why this was chosen>"}},
        "beverage": {{"dish_id": "<id>", "name": "<name>", "reason": "<why this was chosen>"}}
    }},
    "meal_notes": "<overall explanation of the meal plan>"
}}

You can omit categories if not requested. Only include categories from: {', '.join(preferences.get('meal_types', ['main']))}.
Return ONLY the JSON object, nothing else."""

        response = call_gemini(prompt)
        
        if not response:
            return None
        
        # Clean response
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON
        meal_plan_data = json.loads(response)
        
        # Validate and enrich with dish data
        meal_plan = meal_plan_data.get('meal_plan', {})
        dishes_dict = {d.id: d for d in filtered_dishes}
        
        # Category mapping (AI might return singular, we use plural in system)
        category_map = {
            'appetizer': 'appetizers',
            'main': 'main',
            'dessert': 'desserts',
            'beverage': 'beverages'
        }
        
        result_dishes = {}
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        
        for category_key, dish_info in meal_plan.items():
            dish_id = dish_info.get('dish_id')
            dish = dishes_dict.get(dish_id)
            
            # Map category to system format
            category = category_map.get(category_key, category_key)
            
            if dish:
                dish_data = {
                    'id': dish.id,
                    'name': dish.name,
                    'description': dish.description,
                    'price': dish.price,
                    'image': dish.image,
                    'category': dish.category,
                    'reason': dish_info.get('reason', ''),
                    'nutrition': dish.nutritional_info
                }
                
                if dish.nutritional_info:
                    n = dish.nutritional_info
                    total_calories += n.get('calories', 0)
                    total_protein += n.get('protein', 0)
                    total_carbs += n.get('carbs', 0)
                    total_fat += n.get('fat', 0)
                    total_fiber += n.get('fiber', 0)
                
                result_dishes[category] = dish_data
            else:
                print(f"Warning: Dish with ID {dish_id} not found in filtered dishes")
        
        return {
            'dishes': result_dishes,
            'total_nutrition': {
                'calories': round(total_calories),
                'protein': round(total_protein, 1),
                'carbs': round(total_carbs, 1),
                'fat': round(total_fat, 1),
                'fiber': round(total_fiber, 1)
            },
            'meal_notes': meal_plan_data.get('meal_notes', ''),
            'total_price': sum(d['price'] for d in result_dishes.values())
        }
        
    except Exception as e:
        print(f"Error generating meal plan: {e}")
        import traceback
        traceback.print_exc()
        return None