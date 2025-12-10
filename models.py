"""
Data models for the Restaurant Order System
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

class User:
    """User model for customers, employees, and managers"""
    def __init__(self, username: str, password_hash: str, role: str = 'customer', 
                 email: str = '', balance: float = 0.0, **kwargs):
        self.id = kwargs.get('id', username)  # Use username as ID
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.role = role  # 'visitor', 'customer', 'vip', 'chef', 'delivery', 'manager'
        self.balance = balance
        self.warnings = kwargs.get('warnings', 0)
        self.total_spent = kwargs.get('total_spent', 0.0)
        self.orders_count = kwargs.get('orders_count', 0)
        self.complaints_count = kwargs.get('complaints_count', 0)
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.approved = kwargs.get('approved', False)  # For customer registration approval
        self.blacklisted = kwargs.get('blacklisted', False)  # Blacklist flag
        self.closure_requested = kwargs.get('closure_requested', False)  # Account closure request flag
        
        # Employee-specific fields
        self.salary = kwargs.get('salary', 0.0)
        self.rating = kwargs.get('rating', 0.0)  # Average rating
        self.ratings_count = kwargs.get('ratings_count', 0)
        self.compliments = kwargs.get('compliments', 0)
        self.demotions = kwargs.get('demotions', 0)
        self.bonuses = kwargs.get('bonuses', 0)
        
        # Chef-specific
        self.specialty = kwargs.get('specialty', '')
        self.dishes_created = kwargs.get('dishes_created', 0)
        
        # Delivery-specific
        self.deliveries_completed = kwargs.get('deliveries_completed', 0)
        
        # VIP-specific
        self.vip_since = kwargs.get('vip_since', None)
        self.free_deliveries_used = kwargs.get('free_deliveries_used', 0)
        self.free_deliveries_earned = kwargs.get('free_deliveries_earned', 0)
        
        # Flavor profile (for recommendations)
        self.flavor_profile = kwargs.get('flavor_profile', {
            'spicy': 0, 'sweet': 0, 'savory': 0, 'tangy': 0
        })
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary for JSON storage"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'role': self.role,
            'balance': self.balance,
            'warnings': self.warnings,
            'total_spent': self.total_spent,
            'orders_count': self.orders_count,
            'complaints_count': self.complaints_count,
            'created_at': self.created_at,
            'approved': self.approved,
            'blacklisted': self.blacklisted,
            'closure_requested': self.closure_requested,
            'salary': self.salary,
            'rating': self.rating,
            'ratings_count': self.ratings_count,
            'compliments': self.compliments,
            'demotions': self.demotions,
            'bonuses': self.bonuses,
            'specialty': self.specialty,
            'dishes_created': self.dishes_created,
            'deliveries_completed': self.deliveries_completed,
            'vip_since': self.vip_since,
            'free_deliveries_used': self.free_deliveries_used,
            'free_deliveries_earned': self.free_deliveries_earned,
            'flavor_profile': self.flavor_profile
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create user from dictionary"""
        return cls(**data)

class Dish:
    """Dish model for menu items"""
    def __init__(self, name: str, description: str, price: float, chef_id: str,
                 category: str = 'main', **kwargs):
        self.id = kwargs.get('id', f"dish_{datetime.now().timestamp()}")
        self.name = name
        self.description = description
        self.price = price
        self.chef_id = chef_id
        self.category = category  # 'appetizers', 'main', 'desserts', 'beverages'
        self.image = kwargs.get('image', '/static/images/default_dish.png')
        self.rating = kwargs.get('rating', 0.0)
        self.ratings_count = kwargs.get('ratings_count', 0)
        self.orders_count = kwargs.get('orders_count', 0)
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.available = kwargs.get('available', True)
        self.vip_only = kwargs.get('vip_only', False)
        
        # Flavor tags for recommendations
        self.flavor_tags = kwargs.get('flavor_tags', [])  # ['spicy', 'sweet', etc.]
        
        # Nutritional information (AI-estimated)
        # Format: {'calories': int, 'protein': float, 'carbs': float, 'fat': float, 'fiber': float, 
        #          'allergens': List[str], 'dietary_tags': List[str]}
        self.nutritional_info = kwargs.get('nutritional_info', None)
    
    def to_dict(self) -> Dict:
        """Convert dish to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'chef_id': self.chef_id,
            'category': self.category,
            'image': self.image,
            'rating': self.rating,
            'ratings_count': self.ratings_count,
            'orders_count': self.orders_count,
            'created_at': self.created_at,
            'available': self.available,
            'vip_only': self.vip_only,
            'flavor_tags': self.flavor_tags,
            'nutritional_info': self.nutritional_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Dish':
        """Create dish from dictionary"""
        return cls(**data)

class Order:
    """Order model"""
    def __init__(self, customer_id: str, items: List[Dict], total: float, **kwargs):
        import random
        import string
        import time
        import uuid
        # Generate unique order ID: timestamp + UUID short + random string
        if 'id' not in kwargs:
            # Use time.time_ns() for nanosecond precision, or fallback to microsecond precision
            try:
                # Python 3.7+ has time.time_ns()
                timestamp_ns = time.time_ns()
                # Use last 10 digits of nanosecond timestamp for shorter ID
                timestamp_str = str(timestamp_ns)[-10:]
            except AttributeError:
                # Fallback for older Python versions
                timestamp_us = int(datetime.now().timestamp() * 1000000)  # microseconds
                timestamp_str = str(timestamp_us)[-10:]
            
            # Add UUID hex (first 8 chars) for guaranteed uniqueness
            uuid_short = str(uuid.uuid4().hex)[:8].upper()
            
            # Add random string for extra uniqueness
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            self.id = f"ORD{timestamp_str}{uuid_short}{random_str}"
        else:
            self.id = kwargs.get('id')
        self.customer_id = customer_id
        self.items = items  # [{'dish_id': '...', 'quantity': 2, 'price': 10.0}]
        self.total = total
        self.status = kwargs.get('status', 'pending')  # 'pending', 'preparing', 'ready', 'delivering', 'delivered', 'cancelled'
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.delivery_person_id = kwargs.get('delivery_person_id', None)
        self.delivery_bid = kwargs.get('delivery_bid', None)
        self.food_rating = kwargs.get('food_rating', None)  # 1-5
        self.delivery_rating = kwargs.get('delivery_rating', None)  # 1-5
        self.discount_applied = kwargs.get('discount_applied', 0.0)
        self.free_delivery = kwargs.get('free_delivery', False)
        self.delivery_fee = kwargs.get('delivery_fee', 0.0)  # 10% of order total
        self.delivery_address = kwargs.get('delivery_address', '')  # Customer delivery address
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'items': self.items,
            'total': self.total,
            'status': self.status,
            'created_at': self.created_at,
            'delivery_person_id': self.delivery_person_id,
            'delivery_bid': self.delivery_bid,
            'food_rating': self.food_rating,
            'delivery_rating': self.delivery_rating,
            'discount_applied': self.discount_applied,
            'free_delivery': self.free_delivery,
            'delivery_fee': self.delivery_fee,
            'delivery_address': self.delivery_address
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Order':
        """Create order from dictionary"""
        return cls(**data)

class Rating:
    """Rating model for dishes and delivery"""
    def __init__(self, order_id: str, rated_entity_id: str, entity_type: str,
                 rating: int, **kwargs):
        self.id = kwargs.get('id', f"rating_{datetime.now().timestamp()}")
        self.order_id = order_id
        self.rated_entity_id = rated_entity_id  # dish_id or delivery_person_id
        self.entity_type = entity_type  # 'dish' or 'delivery'
        self.rating = rating  # 1-5
        self.comment = kwargs.get('comment', '')
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.user_id = kwargs.get('user_id', '')
    
    def to_dict(self) -> Dict:
        """Convert rating to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'rated_entity_id': self.rated_entity_id,
            'entity_type': self.entity_type,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at,
            'user_id': self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Rating':
        """Create rating from dictionary"""
        return cls(**data)

class Complaint:
    """Complaint/Compliment model"""
    def __init__(self, complainant_id: str, target_id: str, target_type: str,
                 complaint_type: str, description: str, **kwargs):
        self.id = kwargs.get('id', f"complaint_{datetime.now().timestamp()}")
        self.complainant_id = complainant_id
        self.target_id = target_id  # user_id, chef_id, or delivery_person_id
        self.target_type = target_type  # 'chef', 'delivery', 'customer'
        self.complaint_type = complaint_type  # 'complaint' or 'compliment'
        self.description = description
        self.status = kwargs.get('status', 'pending')  # 'pending', 'resolved', 'disputed', 'dismissed'
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.resolved_by = kwargs.get('resolved_by', None)
        self.resolved_at = kwargs.get('resolved_at', None)
        self.disputed = kwargs.get('disputed', False)
        self.dispute_resolution = kwargs.get('dispute_resolution', None)  # 'upheld', 'dismissed'
    
    def to_dict(self) -> Dict:
        """Convert complaint to dictionary"""
        return {
            'id': self.id,
            'complainant_id': self.complainant_id,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'complaint_type': self.complaint_type,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at,
            'disputed': self.disputed,
            'dispute_resolution': self.dispute_resolution
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Complaint':
        """Create complaint from dictionary"""
        return cls(**data)

class ForumPost:
    """Forum post model"""
    def __init__(self, author_id: str, title: str, content: str, category: str, **kwargs):
        self.id = kwargs.get('id', f"post_{datetime.now().timestamp()}")
        self.author_id = author_id
        self.title = title
        self.content = content
        self.category = category  # 'chefs', 'dishes', 'delivery', 'general'
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.replies = kwargs.get('replies', [])  # List of reply dictionaries
        self.likes = kwargs.get('likes', 0)
        self.views = kwargs.get('views', 0)
    
    def to_dict(self) -> Dict:
        """Convert forum post to dictionary"""
        return {
            'id': self.id,
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'created_at': self.created_at,
            'replies': self.replies,
            'likes': self.likes,
            'views': self.views
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ForumPost':
        """Create forum post from dictionary"""
        return cls(**data)

class DeliveryBid:
    """Delivery bid model"""
    def __init__(self, order_id: str, delivery_person_id: str, bid_amount: float, **kwargs):
        self.id = kwargs.get('id', f"bid_{datetime.now().timestamp()}")
        self.order_id = order_id
        self.delivery_person_id = delivery_person_id
        self.bid_amount = bid_amount
        self.status = kwargs.get('status', 'pending')  # 'pending', 'accepted', 'rejected'
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.manager_memo = kwargs.get('manager_memo', None)  # Memo when choosing higher bid
    
    def to_dict(self) -> Dict:
        """Convert delivery bid to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'delivery_person_id': self.delivery_person_id,
            'bid_amount': self.bid_amount,
            'status': self.status,
            'created_at': self.created_at,
            'manager_memo': self.manager_memo
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DeliveryBid':
        """Create delivery bid from dictionary"""
        return cls(**data)
