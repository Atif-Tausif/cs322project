"""
Authentication and session management
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from database import get_user_by_username, get_user_by_id
from utils import verify_password

def login_user(username: str, password: str) -> tuple:
    """
    Attempt to login a user
    Returns: (success: bool, user: User or None, message: str)
    """
    user = get_user_by_username(username)
    
    if not user:
        return False, None, "Invalid username or password"
    
    if not verify_password(password, user.password_hash):
        return False, None, "Invalid username or password"
    
    if user.role in ['customer', 'vip'] and not user.approved:
        return False, None, "Your account is pending manager approval"
    
    # Set session
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['user'] = user.to_dict()  # Store user data in session
    
    return True, user, "Login successful"

def logout_user():
    """Logout current user"""
    session.clear()

def get_current_user():
    """Get current logged-in user"""
    if 'user_id' not in session:
        return None
    
    user = get_user_by_id(session['user_id'])
    if user:
        # Update session with latest user data (including role changes)
        session['user'] = user.to_dict()
        session['role'] = user.role  # Update role in session
        session.modified = True  # Mark session as modified
        return user
    return None

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page', 'warning')
                return redirect(url_for('login', next=request.url))
            
            user_role = session.get('role')
            if user_role not in roles:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_approved(f):
    """Decorator to require approved account"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        
        user = get_current_user()
        if user and user.role in ['customer', 'vip'] and not user.approved:
            flash('Your account is pending manager approval', 'warning')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function
