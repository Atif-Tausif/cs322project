"""
JSON-based database operations
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from config import DATA_DIR
from models import User, Dish, Order, Rating, Complaint, ForumPost, DeliveryBid

# File paths
USERS_FILE = DATA_DIR / "users.json"
DISHES_FILE = DATA_DIR / "dishes.json"
ORDERS_FILE = DATA_DIR / "orders.json"
RATINGS_FILE = DATA_DIR / "ratings.json"
COMPLAINTS_FILE = DATA_DIR / "complaints.json"
FORUM_POSTS_FILE = DATA_DIR / "forum_posts.json"
DELIVERY_BIDS_FILE = DATA_DIR / "delivery_bids.json"
KNOWLEDGE_BASE_FILE = DATA_DIR / "knowledge_base.json"
KNOWLEDGE_RATINGS_FILE = DATA_DIR / "knowledge_ratings.json"

def ensure_data_dir():
    """Ensure data directory exists"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_json(file_path: Path, default: List = None) -> List[Dict]:
    """Load JSON data from file"""
    if default is None:
        default = []
    
    ensure_data_dir()
    
    if not file_path.exists():
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else default
    except (json.JSONDecodeError, IOError):
        return default

def save_json(file_path: Path, data: List[Dict]):
    """Save JSON data to file"""
    ensure_data_dir()
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# User operations
def get_all_users() -> List[User]:
    """Get all users"""
    data = load_json(USERS_FILE, [])
    return [User.from_dict(u) for u in data]

def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID"""
    users = get_all_users()
    return next((u for u in users if u.id == user_id), None)

def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    users = get_all_users()
    return next((u for u in users if u.username == username), None)

def save_user(user: User):
    """Save or update user"""
    users = get_all_users()
    
    # Find existing user by ID
    existing_index = next((i for i, u in enumerate(users) if u.id == user.id), None)
    
    if existing_index is not None:
        # Update existing user
        users[existing_index] = user
    else:
        # Add new user
        users.append(user)
    
    # Save to JSON file
    save_json(USERS_FILE, [u.to_dict() for u in users])

def delete_user(user_id: str):
    """Delete user"""
    users = get_all_users()
    users = [u for u in users if u.id != user_id]
    save_json(USERS_FILE, [u.to_dict() for u in users])

# Dish operations
def get_all_dishes() -> List[Dish]:
    """Get all dishes"""
    data = load_json(DISHES_FILE, [])
    return [Dish.from_dict(d) for d in data]

def get_dish_by_id(dish_id: str) -> Optional[Dish]:
    """Get dish by ID"""
    dishes = get_all_dishes()
    return next((d for d in dishes if d.id == dish_id), None)

def save_dish(dish: Dish):
    """Save or update dish"""
    dishes = get_all_dishes()
    existing_index = next((i for i, d in enumerate(dishes) if d.id == dish.id), None)
    
    if existing_index is not None:
        dishes[existing_index] = dish
    else:
        dishes.append(dish)
    
    save_json(DISHES_FILE, [d.to_dict() for d in dishes])

def delete_dish(dish_id: str):
    """Delete dish"""
    dishes = get_all_dishes()
    dishes = [d for d in dishes if d.id != dish_id]
    save_json(DISHES_FILE, [d.to_dict() for d in dishes])

# Order operations
def get_all_orders() -> List[Order]:
    """Get all orders"""
    data = load_json(ORDERS_FILE, [])
    return [Order.from_dict(o) for o in data]

def get_order_by_id(order_id: str) -> Optional[Order]:
    """Get order by ID"""
    orders = get_all_orders()
    return next((o for o in orders if o.id == order_id), None)

def get_orders_by_customer(customer_id: str) -> List[Order]:
    """Get orders by customer ID"""
    orders = get_all_orders()
    return [o for o in orders if o.customer_id == customer_id]

def save_order(order: Order):
    """Save or update order"""
    orders = get_all_orders()
    existing_index = next((i for i, o in enumerate(orders) if o.id == order.id), None)
    
    if existing_index is not None:
        orders[existing_index] = order
    else:
        orders.append(order)
    
    save_json(ORDERS_FILE, [o.to_dict() for o in orders])

# Rating operations
def get_all_ratings() -> List[Rating]:
    """Get all ratings"""
    data = load_json(RATINGS_FILE, [])
    return [Rating.from_dict(r) for r in data]

def get_ratings_by_entity(entity_id: str, entity_type: str) -> List[Rating]:
    """Get ratings for a specific entity"""
    ratings = get_all_ratings()
    return [r for r in ratings if r.rated_entity_id == entity_id and r.entity_type == entity_type]

def save_rating(rating: Rating):
    """Save rating"""
    ratings = get_all_ratings()
    ratings.append(rating)
    save_json(RATINGS_FILE, [r.to_dict() for r in ratings])

# Complaint operations
def get_all_complaints() -> List[Complaint]:
    """Get all complaints"""
    data = load_json(COMPLAINTS_FILE, [])
    return [Complaint.from_dict(c) for c in data]

def get_complaints_by_target(target_id: str) -> List[Complaint]:
    """Get complaints for a specific target"""
    complaints = get_all_complaints()
    return [c for c in complaints if c.target_id == target_id]

def save_complaint(complaint: Complaint):
    """Save or update complaint"""
    complaints = get_all_complaints()
    existing_index = next((i for i, c in enumerate(complaints) if c.id == complaint.id), None)
    
    if existing_index is not None:
        complaints[existing_index] = complaint
    else:
        complaints.append(complaint)
    
    save_json(COMPLAINTS_FILE, [c.to_dict() for c in complaints])

# Forum post operations
def get_all_forum_posts() -> List[ForumPost]:
    """Get all forum posts"""
    data = load_json(FORUM_POSTS_FILE, [])
    return [ForumPost.from_dict(p) for p in data]

def get_forum_post_by_id(post_id: str) -> Optional[ForumPost]:
    """Get forum post by ID"""
    posts = get_all_forum_posts()
    return next((p for p in posts if p.id == post_id), None)

def save_forum_post(post: ForumPost):
    """Save or update forum post"""
    posts = get_all_forum_posts()
    existing_index = next((i for i, p in enumerate(posts) if p.id == post.id), None)
    
    if existing_index is not None:
        posts[existing_index] = post
    else:
        posts.append(post)
    
    save_json(FORUM_POSTS_FILE, [p.to_dict() for p in posts])

# Delivery bid operations
def get_all_delivery_bids() -> List[DeliveryBid]:
    """Get all delivery bids"""
    data = load_json(DELIVERY_BIDS_FILE, [])
    return [DeliveryBid.from_dict(b) for b in data]

def get_bids_by_order(order_id: str) -> List[DeliveryBid]:
    """Get bids for a specific order"""
    bids = get_all_delivery_bids()
    return [b for b in bids if b.order_id == order_id and b.status == 'pending']

def save_delivery_bid(bid: DeliveryBid):
    """Save or update delivery bid"""
    bids = get_all_delivery_bids()
    existing_index = next((i for i, b in enumerate(bids) if b.id == bid.id), None)
    
    if existing_index is not None:
        bids[existing_index] = bid
    else:
        bids.append(bid)
    
    save_json(DELIVERY_BIDS_FILE, [b.to_dict() for b in bids])

# Knowledge base operations
def get_knowledge_base() -> List[Dict]:
    """Get all knowledge base entries"""
    data = load_json(KNOWLEDGE_BASE_FILE, [])
    # Merge with default knowledge base from config
    from config import KNOWLEDGE_BASE as DEFAULT_KB
    default_ids = {hash(entry['question']) for entry in DEFAULT_KB}
    user_entries = [e for e in data if e.get('id') not in default_ids]
    return DEFAULT_KB + user_entries

def save_knowledge_entry(entry: Dict):
    """Save a knowledge base entry"""
    entries = load_json(KNOWLEDGE_BASE_FILE, [])
    entry['id'] = entry.get('id', f"kb_{hash(entry.get('question', ''))}")
    entry['approved'] = entry.get('approved', False)  # Requires manager approval
    entry['author_id'] = entry.get('author_id', '')
    entries.append(entry)
    save_json(KNOWLEDGE_BASE_FILE, entries)

def delete_knowledge_entry(entry_id: str):
    """Delete a knowledge base entry"""
    entries = load_json(KNOWLEDGE_BASE_FILE, [])
    entries = [e for e in entries if e.get('id') != entry_id]
    save_json(KNOWLEDGE_BASE_FILE, entries)

def save_knowledge_rating(entry_id: str, rating: int, user_id: str):
    """Save rating for knowledge base entry"""
    ratings = load_json(KNOWLEDGE_RATINGS_FILE, [])
    ratings.append({
        'entry_id': entry_id,
        'rating': rating,
        'user_id': user_id,
        'created_at': datetime.now().isoformat()
    })
    save_json(KNOWLEDGE_RATINGS_FILE, ratings)
    
    # If rating is 0, flag for manager review
    if rating == 0:
        # Get entry and flag it
        entries = get_knowledge_base()
        entry = next((e for e in entries if e.get('id') == entry_id), None)
        if entry:
            entry['flagged'] = True
            entry['flagged_by'] = user_id
            if entry.get('id', '').startswith('kb_'):
                # User-contributed entry, save to file
                user_entries = load_json(KNOWLEDGE_BASE_FILE, [])
                for i, e in enumerate(user_entries):
                    if e.get('id') == entry_id:
                        user_entries[i] = entry
                        save_json(KNOWLEDGE_BASE_FILE, user_entries)
                        break

def get_flagged_knowledge_entries() -> List[Dict]:
    """Get flagged knowledge base entries for manager review"""
    entries = get_knowledge_base()
    return [e for e in entries if e.get('flagged', False)]

def reset_database():
    """Reset all database files (for initialization)"""
    ensure_data_dir()
    for file_path in [USERS_FILE, DISHES_FILE, ORDERS_FILE, RATINGS_FILE, 
                      COMPLAINTS_FILE, FORUM_POSTS_FILE, DELIVERY_BIDS_FILE,
                      KNOWLEDGE_BASE_FILE, KNOWLEDGE_RATINGS_FILE]:
        if file_path.exists():
            file_path.unlink()
