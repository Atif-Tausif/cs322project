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
    PROVIDER = os.environ.get('LLM_PROVIDER', 'gemini')

    # Ollama
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')

    # HuggingFace
    HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN', '')
    HUGGINGFACE_MODEL = os.environ.get('HUGGINGFACE_MODEL', 'tiiuae/falcon-7b-instruct')
    HUGGINGFACE_API_URL = 'https://router.huggingface.co'

    # Gemini
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDksrXk3tM2rEKCd9gr8TTOo16_ue3BLkY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


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
