"""
Configuration settings for the Restaurant Order System
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Data directory for JSON files
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Flask Configuration
class FlaskConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
    
# LLM Configuration
class LLMConfig:
    # Using HuggingFace only
    PROVIDER = 'huggingface'
    
    # HuggingFace settings
    HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN', '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')
    HUGGINGFACE_MODEL = os.environ.get('HUGGINGFACE_MODEL', 'microsoft/DialoGPT-medium')
    HUGGINGFACE_API_URL = 'https://api-inference.huggingface.co/models'
    
    # Timeout for API calls (seconds)
    TIMEOUT = 30

# Application Settings
class AppConfig:
    # VIP Requirements
    VIP_SPENDING_THRESHOLD = 100.0  # $100 total spending
    VIP_ORDERS_WITHOUT_COMPLAINTS = 3  # 3 orders without complaints
    
    # VIP Benefits
    VIP_DISCOUNT_PERCENT = 5  # 5% discount
    VIP_FREE_DELIVERY_RATIO = 3  # 1 free delivery per 3 orders
    
    # Warning System
    MAX_WARNINGS_BEFORE_DEREGISTRATION = 3
    MAX_WARNINGS_FOR_VIP_DOWNGRADE = 2
    
    # Employee Performance
    LOW_RATING_THRESHOLD = 2.0  # Rating below this triggers demotion
    HIGH_RATING_THRESHOLD = 4.0  # Rating above this triggers bonus
    COMPLAINTS_FOR_DEMOTION = 3
    COMPLIMENTS_FOR_BONUS = 3
    DEMOTIONS_BEFORE_FIRING = 2
    
    # Financial
    MIN_DEPOSIT = 0.0  # Minimum deposit required
    
    # Pagination
    DISHES_PER_PAGE = 12
    ORDERS_PER_PAGE = 10
    FORUM_POSTS_PER_PAGE = 20
    
    # File Upload
    UPLOAD_FOLDER = BASE_DIR / "static" / "images"
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Knowledge Base (for AI chat)
KNOWLEDGE_BASE = [
    {
        "question": "What are your hours?",
        "answer": "We're open Monday through Sunday from 11:00 AM to 10:00 PM.",
        "tags": ["hours", "time", "open"]
    },
    {
        "question": "Do you offer delivery?",
        "answer": "Yes! We offer delivery service. VIP members get 1 free delivery per 3 orders.",
        "tags": ["delivery", "shipping"]
    },
    {
        "question": "How do I become a VIP member?",
        "answer": "You can become a VIP member by spending $100 or by making 3 orders without any complaints. VIP members enjoy a 5% discount and free delivery benefits!",
        "tags": ["vip", "membership", "benefits"]
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We use a deposit-based system. You need to maintain a balance in your account to place orders.",
        "tags": ["payment", "deposit", "balance"]
    },
    {
        "question": "Can I cancel my order?",
        "answer": "Please contact our customer service through the chat if you need to cancel an order. Cancellation policies may vary based on order status.",
        "tags": ["cancel", "order", "refund"]
    },
    {
        "question": "How do I rate a dish?",
        "answer": "After receiving your order, you can rate both the food (1-5 stars) and delivery service (1-5 stars) separately on your order history page.",
        "tags": ["rating", "review", "feedback"]
    }
]
