"""
Utility functions
"""
import bcrypt
import os
from werkzeug.utils import secure_filename
from config import AppConfig
from PIL import Image
import hashlib

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in AppConfig.ALLOWED_EXTENSIONS

def save_uploaded_image(file, folder: str = 'dishes') -> str:
    """Save uploaded image file and return path"""
    if not file or not allowed_file(file.filename):
        return None
    
    # Create folder if it doesn't exist
    upload_folder = AppConfig.UPLOAD_FOLDER / folder
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    unique_name = f"{name}_{hashlib.md5(name.encode()).hexdigest()[:8]}{ext}"
    filepath = upload_folder / unique_name
    
    # Save file
    file.save(str(filepath))
    
    # Resize if needed (optional)
    try:
        img = Image.open(filepath)
        if img.width > 800 or img.height > 800:
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img.save(filepath)
    except Exception:
        pass
    
    # Return relative path
    return f"/static/images/{folder}/{unique_name}"

def calculate_discount(user, total: float) -> float:
    """Calculate discount for VIP users"""
    if user.role == 'vip':
        return total * (AppConfig.VIP_DISCOUNT_PERCENT / 100)
    return 0.0

def calculate_flavor_match(user_flavor_profile: dict, dish_flavor_tags: list) -> float:
    """Calculate flavor match percentage between user profile and dish tags"""
    if not dish_flavor_tags:
        return 0.0
    
    total_score = 0.0
    max_score = 0.0
    
    for tag in dish_flavor_tags:
        user_score = user_flavor_profile.get(tag, 0)
        total_score += user_score
        max_score += 10  # Assuming max score per tag is 10
    
    if max_score == 0:
        return 0.0
    
    match_percentage = (total_score / max_score) * 100
    return min(100.0, max(0.0, match_percentage))

def update_user_flavor_profile(user, dish_flavor_tags: list, rating: int):
    """Update user's flavor profile based on dish rating"""
    if not dish_flavor_tags or rating < 1:
        return
    
    # Increase profile scores for tags in dishes that user rated highly
    increment = (rating - 3) * 0.5  # Positive rating increases, negative decreases
    
    for tag in dish_flavor_tags:
        if tag in user.flavor_profile:
            user.flavor_profile[tag] = max(0, min(10, user.flavor_profile[tag] + increment))

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:.2f}"

def calculate_average_rating(ratings: list) -> float:
    """Calculate average rating from list of rating values"""
    if not ratings:
        return 0.0
    return sum(ratings) / len(ratings)
