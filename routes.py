"""
Flask routes and endpoints
"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from auth import login_user, logout_user, get_current_user, require_login, require_role, require_approved
from database import (
    get_all_dishes, get_dish_by_id, save_dish, get_all_users, get_user_by_id, save_user,
    get_orders_by_customer, get_order_by_id, get_all_orders, get_bids_by_order,
    get_all_forum_posts, get_forum_post_by_id, save_forum_post, delete_user, save_order
)
from services import (
    process_order, submit_rating, file_complaint, resolve_complaint, dispute_complaint,
    submit_delivery_bid, accept_delivery_bid,
    get_popular_dishes, get_top_rated_dishes, get_featured_chefs
)
from ai_service import get_ai_response, get_personalized_recommendations, get_flavor_profile_analysis, estimate_nutritional_info
from models import User, Dish, Order, Complaint, ForumPost
from utils import hash_password, save_uploaded_image
from config import AppConfig
import json

bp = Blueprint('main', __name__)

# ============================================================================
# Home & Public Routes
# ============================================================================

@bp.route('/')
def index():
    """Home page"""
    popular_dishes = get_popular_dishes(6)
    top_rated_dishes = get_top_rated_dishes(6)
    featured_chefs = get_featured_chefs(4)
    
    # Add chef names to dishes
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}
    for dish in popular_dishes + top_rated_dishes:
        dish['chef_name'] = chefs.get(dish.get('chef_id'), 'Unknown')
    
    return render_template('index.html',
                         popular_dishes=popular_dishes,
                         top_rated_dishes=top_rated_dishes,
                         featured_chefs=featured_chefs)

@bp.route('/menu')
def menu():
    """Menu page"""
    chefs = [u for u in get_all_users() if u.role == 'chef' and u.approved]
    return render_template('menu.html', chefs=chefs)

@bp.route('/dish/<dish_id>')
def dish_detail(dish_id):
    """Dish detail page"""
    dish = get_dish_by_id(dish_id)
    if not dish:
        flash('Dish not found', 'danger')
        return redirect(url_for('main.menu'))
    
    chef = get_user_by_id(dish.chef_id)
    dish_dict = dish.to_dict()
    dish_dict['chef_name'] = chef.username if chef else 'Unknown'
    
    # Try to get nutritional info if not cached (will be calculated via AJAX if needed)
    # We don't calculate here to avoid slowing down page load
    
    return render_template('dish_detail.html', dish=dish_dict)

# ============================================================================
# Authentication Routes
# ============================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        success, user, message = login_user(username, password)
        
        if success:
            flash(message, 'success')
            next_url = request.args.get('next', url_for('main.index'))
            return redirect(next_url)
        else:
            flash(message, 'danger')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')
        
        # Check if username exists
        existing = get_user_by_id(username)
        if existing:
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        # Check if user is blacklisted (by username or email)
        all_users = get_all_users()
        blacklisted_user = next((u for u in all_users if (u.username == username or u.email == email) and u.blacklisted), None)
        if blacklisted_user:
            flash('This account has been blacklisted and cannot register again', 'danger')
            return render_template('register.html')
        
        # Create new user
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            role='customer',
            approved=False  # Requires manager approval
        )
        save_user(user)
        
        flash('Registration successful! Please wait for manager approval.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')

@bp.route('/logout')
def logout():
    """Logout"""
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('main.index'))

# ============================================================================
# Customer Routes
# ============================================================================

@bp.route('/profile')
@require_login
@require_approved
def profile():
    """User profile page"""
    user = get_current_user()
    
    # Force reload from database to ensure we have the latest data
    # This is important after role changes like VIP downgrade
    user = get_user_by_id(user.id)
    
    # Update session with latest data
    session['user'] = user.to_dict()
    session['role'] = user.role
    session.modified = True
    
    orders = get_orders_by_customer(user.id)
    
    # Get complaints against this user
    from database import get_complaints_by_target
    my_complaints = get_complaints_by_target(user.id)
    
    # Get flavor profile analysis for VIP (only if actually VIP)
    flavor_analysis = None
    if user.role == 'vip':
        flavor_analysis = get_flavor_profile_analysis(user.id)
    
    # Get flavor preferences from order history for all customers
    flavor_preferences = None
    if user.role in ['customer', 'vip']:
        from ai_service import get_flavor_preferences_from_orders
        flavor_preferences = get_flavor_preferences_from_orders(user.id)
    
    # Get chefs, delivery persons, and customers for complaint/compliment form (only for customers/VIPs)
    chefs = []
    delivery_persons = []
    customers = []
    if user.role in ['customer', 'vip']:
        all_users = get_all_users()
        chefs = [u.to_dict() for u in all_users if u.role == 'chef' and u.approved]
        delivery_persons = [u.to_dict() for u in all_users if u.role == 'delivery' and u.approved]
        customers = [u.to_dict() for u in all_users if u.role in ['customer', 'vip'] and u.approved and u.id != user.id]
    
    return render_template('profile.html', user=user, orders=orders[:10], 
                         flavor_analysis=flavor_analysis, flavor_preferences=flavor_preferences,
                         my_complaints=my_complaints, chefs=chefs, delivery_persons=delivery_persons, customers=customers)

@bp.route('/orders')
@require_login
@require_approved
def orders():
    """Order history page"""
    user = get_current_user()
    orders = get_orders_by_customer(user.id)
    
    # Add dish names and prices to orders
    dishes = {d.id: d for d in get_all_dishes()}
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}  # ✅ Add chef names
    delivery_people = {u.id: u.username for u in get_all_users() if u.role == 'delivery'}  # ✅ Add delivery names
    
    for order in orders:
        # ✅ Add delivery person name
        if order.delivery_person_id:
            order.delivery_person_name = delivery_people.get(order.delivery_person_id, 'Unknown')
        
        for item in order.items:
            dish = dishes.get(item.get('dish_id'))
            if dish:
                item['dish_name'] = dish.name
                item['dish_image'] = dish.image
                item['price'] = item.get('price', dish.price)
                # ✅ ADD THE FULL DISH OBJECT with chef info
                dish_dict = dish.to_dict()
                dish_dict['chef_name'] = chefs.get(dish.chef_id, 'Unknown')
                item['dish'] = dish_dict
    
    return render_template('orders.html', orders=orders)

@bp.route('/cart')
@require_login
@require_approved
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', [])
    
    # Add dish details to cart items and validate
    dishes = {d.id: d for d in get_all_dishes()}
    total = 0.0
    valid_items = []
    
    for item in cart_items:
        dish_id = item.get('dish_id')
        quantity = item.get('quantity', 1)
        
        # Validate item
        if not dish_id or not isinstance(quantity, int) or quantity < 1 or quantity > 999:
            continue
            
        dish = dishes.get(dish_id)
        if dish and dish.available:
            item['dish'] = dish.to_dict()
            item['subtotal'] = dish.price * quantity
            total += item['subtotal']
            valid_items.append(item)
    
    # Update session with validated items
    if len(valid_items) != len(cart_items):
        session['cart'] = valid_items
        session.modified = True
    
    user = get_current_user()
    discount = 0.0
    if user.role == 'vip':
        discount = total * (AppConfig.VIP_DISCOUNT_PERCENT / 100)
    
    return render_template('cart.html', cart_items=valid_items, total=total, discount=discount)

@bp.route('/forum')
def forum():
    """Forum page"""
    posts = get_all_forum_posts()
    posts.sort(key=lambda x: x.created_at, reverse=True)
    
    # Add author names
    users = {u.id: u.username for u in get_all_users()}
    for post in posts:
        post.author_name = users.get(post.author_id, 'Unknown')
        # Add author names to replies
        for reply in post.replies:
            reply['author_name'] = users.get(reply.get('author_id'), 'Unknown')
    
    # Get user's orders for reporting chefs and delivery persons
    user_orders = []
    chefs_dict = {}
    delivery_persons_dict = {}
    if session.get('user_id'):
        user = get_current_user()
        if user and user.role in ['customer', 'vip']:
            user_orders = get_orders_by_customer(user.id)
            # Get chefs and delivery persons from orders
            dishes = {d.id: d for d in get_all_dishes()}
            all_users = get_all_users()
            for order in user_orders:
                if order.status == 'delivered':
                    # Get chefs from dishes in order
                    for item in order.items:
                        dish = dishes.get(item.get('dish_id'))
                        if dish and dish.chef_id:
                            chef = next((u for u in all_users if u.id == dish.chef_id), None)
                            if chef and chef.approved:
                                chefs_dict[chef.id] = chef.to_dict()
                    # Get delivery person
                    if order.delivery_person_id:
                        delivery_person = next((u for u in all_users if u.id == order.delivery_person_id), None)
                        if delivery_person and delivery_person.approved:
                            delivery_persons_dict[delivery_person.id] = delivery_person.to_dict()
    
    return render_template('forum.html', posts=posts, 
                         user_orders=user_orders,
                         chefs_dict=chefs_dict,
                         delivery_persons_dict=delivery_persons_dict)

# ============================================================================
# API Endpoints
# ============================================================================

@bp.route('/api/v1/chat', methods=['POST'])
def api_chat():
    """AI chat endpoint"""
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'reply': 'Please enter a message'})
    
    user_id = session.get('user_id')
    response = get_ai_response(message, user_id)
    return jsonify(response)

@bp.route('/api/v1/recommendations')
@require_login
def api_recommendations():
    """Get personalized recommendations"""
    user_id = session.get('user_id')
    dishes = get_personalized_recommendations(user_id, 6)
    
    # Add chef names
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}
    for dish in dishes:
        dish['chef_name'] = chefs.get(dish.get('chef_id'), 'Unknown')
    
    return jsonify({'success': True, 'dishes': dishes})

@bp.route('/api/v1/favorites')
@require_login
def api_favorites():
    """Get user's favorite dishes (most ordered)"""
    user_id = session.get('user_id')
    orders = get_orders_by_customer(user_id)
    
    # Count dish orders
    dish_counts = {}
    for order in orders:
        for item in order.items:
            dish_id = item.get('dish_id')
            dish_counts[dish_id] = dish_counts.get(dish_id, 0) + item.get('quantity', 1)
    
    # Get top dishes
    sorted_dishes = sorted(dish_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    dishes = []
    all_dishes = {d.id: d for d in get_all_dishes()}
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}
    
    for dish_id, count in sorted_dishes:
        dish = all_dishes.get(dish_id)
        if dish and dish.available:
            dish_dict = dish.to_dict()
            dish_dict['chef_name'] = chefs.get(dish.chef_id, 'Unknown')
            dishes.append(dish_dict)
    
    return jsonify({'success': True, 'dishes': dishes})

@bp.route('/api/v1/menu', methods=['GET'])
def api_menu():
    """Get menu dishes with filters"""
    search = request.args.get('search', '').lower()
    category = request.args.get('category', 'all')
    chef = request.args.get('chef', 'all')
    # Handle flavor as either single value or list (from query string)
    flavor = request.args.getlist('flavor') or request.args.get('flavor')
    # If single value, convert to list for consistency
    if flavor and not isinstance(flavor, list):
        flavor = [flavor] if flavor else None
    min_price = float(request.args.get('minPrice', 0))
    max_price = float(request.args.get('maxPrice', 100))
    sort = request.args.get('sort', 'popular')
    page = int(request.args.get('page', 1))
    
    dishes = get_all_dishes()
    
    # Apply filters
    filtered = []
    for dish in dishes:
        if not dish.available:
            continue
        
        # Search filter
        if search and search not in dish.name.lower() and search not in dish.description.lower():
            continue
        
        # Category filter
        if category != 'all' and dish.category != category:
            continue
        
        # Chef filter
        if chef != 'all' and dish.chef_id != chef:
            continue
        
        # Price filter
        if dish.price < min_price or dish.price > max_price:
            continue
        
        # VIP filter
        user = get_current_user()
        if dish.vip_only and (not user or user.role != 'vip'):
            continue
        
        # Flavor filter (all customers) - handle both single flavor and array of flavors
        if flavor:
            # Ensure flavor is a list
            if isinstance(flavor, str):
                flavor_list = [flavor]
            elif isinstance(flavor, list):
                flavor_list = flavor
            else:
                flavor_list = []
            
            # If dish has flavor tags, check if any of the selected flavors match
            if dish.flavor_tags:
                # Check if dish has ANY of the selected flavors
                if not any(f in dish.flavor_tags for f in flavor_list):
                    continue
            else:
                # Dish has no flavor tags, skip if filtering by flavors
                continue
        
        filtered.append(dish)
    
    # Sort
    if sort == 'rating':
        filtered.sort(key=lambda x: x.rating, reverse=True)
    elif sort == 'price-low':
        filtered.sort(key=lambda x: x.price)
    elif sort == 'price-high':
        filtered.sort(key=lambda x: x.price, reverse=True)
    elif sort == 'newest':
        filtered.sort(key=lambda x: x.created_at, reverse=True)
    else:  # popular
        filtered.sort(key=lambda x: x.orders_count, reverse=True)
    
    # Paginate
    per_page = AppConfig.DISHES_PER_PAGE
    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    # Add chef names and flavor match scores
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}
    user = get_current_user()
    flavor_preferences = None
    if user and user.role in ['customer', 'vip']:
        from ai_service import get_flavor_preferences_from_orders
        from utils import calculate_flavor_match
        flavor_preferences = get_flavor_preferences_from_orders(user.id)
    
    dishes_dict = []
    for dish in paginated:
        dish_dict = dish.to_dict()
        dish_dict['chef_name'] = chefs.get(dish.chef_id, 'Unknown')
        # Calculate flavor match if user has preferences
        if flavor_preferences and dish.flavor_tags:
            from utils import calculate_flavor_match
            match_score = calculate_flavor_match(flavor_preferences, dish.flavor_tags)
            dish_dict['match_score'] = round(match_score, 1)
        dishes_dict.append(dish_dict)
    
    return jsonify({
        'success': True,
        'dishes': dishes_dict,
        'total': total,
        'page': page,
        'per_page': per_page
    })

@bp.route('/api/v1/order', methods=['POST'])
@require_login
@require_approved
def api_order():
    """Place an order"""
    data = request.get_json()
    items = data.get('items', [])
    delivery_address = data.get('delivery_address', '').strip()
    
    if not items:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
    if not delivery_address:
        return jsonify({'success': False, 'message': 'Delivery address is required'})
    
    # Calculate total and add prices to items for historical record
    dishes = {d.id: d for d in get_all_dishes()}
    total = 0.0
    for item in items:
        dish = dishes.get(item.get('dish_id'))
        if dish:
            # Store price at time of order for historical accuracy
            item['price'] = dish.price
            total += dish.price * item.get('quantity', 1)
    
    user_id = session.get('user_id')
    success, message, order = process_order(user_id, items, total, delivery_address)
    
    if success:
        # Clear cart
        session['cart'] = []
        session.modified = True
    
    return jsonify({'success': success, 'message': message, 'order_id': order.id if order else None})

@bp.route('/api/v1/rating', methods=['POST'])
@require_login
@require_approved
def api_rating():
    """Submit rating"""
    data = request.get_json()
    order_id = data.get('order_id')
    dish_id = data.get('dish_id')
    food_rating_raw = data.get('food_rating')
    delivery_rating_raw = data.get('delivery_rating')
    delivery_person_id = data.get('delivery_person_id')
    comment = data.get('comment', '')
    
    # Validate food rating
    try:
        food_rating = int(food_rating_raw) if food_rating_raw is not None else 0
    except (ValueError, TypeError):
        food_rating = 0
    
    if not order_id or not dish_id or not (1 <= food_rating <= 5):
        return jsonify({'success': False, 'message': f'Invalid rating data: food_rating={food_rating_raw} (must be 1-5)'})
    
    # Validate delivery rating if provided
    delivery_rating = None
    if delivery_rating_raw is not None:
        try:
            delivery_rating = int(delivery_rating_raw)
            if not (1 <= delivery_rating <= 5):
                delivery_rating = None
        except (ValueError, TypeError):
            delivery_rating = None
    
    user_id = session.get('user_id')
    success, message = submit_rating(
        order_id, user_id, dish_id, food_rating,
        delivery_person_id, delivery_rating, comment
    )
    
    return jsonify({'success': success, 'message': message})

@bp.route('/api/v1/complaint', methods=['POST'])
@require_login
@require_approved
def api_complaint():
    """File complaint/compliment"""
    data = request.get_json()
    target_id = data.get('target_id')
    target_type = data.get('target_type')  # 'chef', 'delivery', 'customer'
    complaint_type = data.get('complaint_type')  # 'complaint' or 'compliment'
    description = data.get('description', '')
    
    if not target_id or not target_type or not complaint_type:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    user_id = session.get('user_id')
    user = get_current_user()
    
    if not user:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    # Delivery personnel can only complain about customers
    if user.role == 'delivery' and target_type != 'customer':
        return jsonify({'success': False, 'message': 'Delivery personnel can only file complaints about customers'})
    
    # Customers can file complaints about chefs, delivery people, or other customers
    if user.role in ['customer', 'vip'] and target_type not in ['chef', 'delivery', 'customer']:
        return jsonify({'success': False, 'message': 'Invalid target type for customers'})
    
    success, message = file_complaint(user_id, target_id, target_type, complaint_type, description)
    
    return jsonify({'success': success, 'message': message})

@bp.route('/api/v1/complaint/dispute', methods=['POST'])
@require_login
@require_approved
def api_dispute_complaint():
    """Dispute a complaint"""
    data = request.get_json()
    complaint_id = data.get('complaint_id')
    
    if not complaint_id:
        return jsonify({'success': False, 'message': 'Complaint ID required'})
    
    user_id = session.get('user_id')
    success, message = dispute_complaint(complaint_id, user_id)
    
    return jsonify({'success': success, 'message': message})

@bp.route('/api/v1/cart/add', methods=['POST'])
@require_login
@require_approved
def api_cart_add():
    """Add item to cart"""
    data = request.get_json()
    dish_id = data.get('dish_id')
    quantity = int(data.get('quantity', 1))
    
    if not dish_id:
        return jsonify({'success': False, 'message': 'Dish ID required'})
    
    # Validate quantity
    if quantity < 1 or quantity > 999:
        return jsonify({'success': False, 'message': 'Invalid quantity. Must be between 1 and 999.'})
    
    dish = get_dish_by_id(dish_id)
    if not dish or not dish.available:
        return jsonify({'success': False, 'message': 'Dish not available'})
    
    # Check VIP access
    user = get_current_user()
    if dish.vip_only and user.role != 'vip':
        return jsonify({'success': False, 'message': 'This dish is VIP only'})
    
    # Add to cart
    cart = session.get('cart', [])
    
    # Check if already in cart
    for item in cart:
        if item.get('dish_id') == dish_id:
            new_quantity = item.get('quantity', 0) + quantity
            if new_quantity > 999:
                return jsonify({'success': False, 'message': 'Maximum quantity per item is 999.'})
            item['quantity'] = new_quantity
            session['cart'] = cart
            session.modified = True
            return jsonify({'success': True, 'message': 'Cart updated', 'cart_count': len(cart)})
    
    # Add new item
    cart.append({
        'dish_id': dish_id,
        'quantity': quantity
    })
    session['cart'] = cart
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Added to cart', 'cart_count': len(cart)})

@bp.route('/api/v1/cart/remove', methods=['POST'])
@require_login
@require_approved
def api_cart_remove():
    """Remove item from cart"""
    data = request.get_json()
    dish_id = data.get('dish_id')
    
    if not dish_id:
        return jsonify({'success': False, 'message': 'Dish ID required'})
    
    cart = session.get('cart', [])
    cart = [item for item in cart if item.get('dish_id') != dish_id]
    session['cart'] = cart
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Removed from cart', 'cart_count': len(cart)})

@bp.route('/api/v1/cart/update', methods=['POST'])
@require_login
@require_approved
def api_cart_update():
    """Update cart item quantity"""
    data = request.get_json()
    dish_id = data.get('dish_id')
    quantity = int(data.get('quantity', 1))
    
    if not dish_id or quantity < 1 or quantity > 999:
        return jsonify({'success': False, 'message': 'Invalid quantity. Must be between 1 and 999.'})
    
    cart = session.get('cart', [])
    for item in cart:
        if item.get('dish_id') == dish_id:
            item['quantity'] = quantity
            session['cart'] = cart
            session.modified = True
            return jsonify({'success': True, 'message': 'Cart updated', 'cart_count': len(cart)})
    
    return jsonify({'success': False, 'message': 'Item not in cart'})

@bp.route('/api/v1/account/closure/request', methods=['POST'])
@require_login
@require_approved
def api_request_account_closure():
    """Request account closure (customer only)"""
    user = get_current_user()
    
    if user.role not in ['customer', 'vip']:
        return jsonify({'success': False, 'message': 'Only customers can request account closure'})
    
    if user.closure_requested:
        return jsonify({'success': False, 'message': 'You have already requested account closure. Please wait for manager review.'})
    
    user.closure_requested = True
    save_user(user)
    
    return jsonify({
        'success': True,
        'message': 'Account closure request submitted. The manager will review your request and make a final decision.'
    })

@bp.route('/api/v1/deposit', methods=['POST'])
@require_login
@require_approved
def api_deposit():
    """Add money to user account"""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Amount must be greater than $0'})
    
    if amount > 10000:
        return jsonify({'success': False, 'message': 'Maximum deposit amount is $10,000'})
    
    user_id = session.get('user_id')
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # Add to balance
    old_balance = user.balance
    user.balance += amount
    save_user(user)
    
    return jsonify({
        'success': True,
        'message': f'Successfully added ${amount:.2f} to your account. New balance: ${user.balance:.2f}',
        'balance': user.balance
    })

@bp.route('/api/v1/knowledge/rate', methods=['POST'])
@require_login
def api_rate_knowledge():
    """Rate a knowledge base entry"""
    data = request.get_json()
    entry_id = data.get('entry_id')
    rating = int(data.get('rating', 0))
    
    if not entry_id:
        return jsonify({'success': False, 'message': 'Entry ID required'})
    
    user_id = session.get('user_id')
    from database import save_knowledge_rating
    save_knowledge_rating(entry_id, rating, user_id)
    
    # If rating is 0, flag for manager
    if rating == 0:
        return jsonify({'success': True, 'message': 'Rating submitted. Entry flagged for manager review.'})
    
    return jsonify({'success': True, 'message': 'Rating submitted'})

@bp.route('/api/v1/knowledge/submit', methods=['POST'])
@require_login
@require_approved
def api_submit_knowledge():
    """Submit a knowledge base entry (customer contribution)"""
    data = request.get_json()
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    tags = data.get('tags', [])
    
    if not question or not answer:
        return jsonify({'success': False, 'message': 'Question and answer are required'})
    
    user_id = session.get('user_id')
    from database import save_knowledge_entry
    save_knowledge_entry({
        'question': question,
        'answer': answer,
        'tags': tags if isinstance(tags, list) else [],
        'author_id': user_id,
        'approved': False  # Requires manager approval
    })
    
    return jsonify({'success': True, 'message': 'Knowledge entry submitted. Pending manager approval.'})

@bp.route('/api/v1/forum/post', methods=['POST'])
@require_login
@require_approved
def api_forum_post():
    """Create a new forum post"""
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    category = data.get('category', 'general')
    
    if not title or not content:
        return jsonify({'success': False, 'message': 'Title and content are required'})
    
    if category not in ['chefs', 'dishes', 'delivery', 'general']:
        return jsonify({'success': False, 'message': 'Invalid category'})
    
    user_id = session.get('user_id')
    user = get_current_user()
    
    # Only registered customers and VIPs can post
    if user.role not in ['customer', 'vip']:
        return jsonify({'success': False, 'message': 'Only registered customers can create posts'})
    
    post = ForumPost(
        author_id=user_id,
        title=title,
        content=content,
        category=category
    )
    
    save_forum_post(post)
    
    return jsonify({'success': True, 'message': 'Post created successfully', 'post_id': post.id})

@bp.route('/api/v1/forum/reply', methods=['POST'])
@require_login
@require_approved
def api_forum_reply():
    """Reply to a forum post"""
    data = request.get_json()
    post_id = data.get('post_id')
    content = data.get('content', '').strip()
    
    if not post_id or not content:
        return jsonify({'success': False, 'message': 'Post ID and content are required'})
    
    post = get_forum_post_by_id(post_id)
    if not post:
        return jsonify({'success': False, 'message': 'Post not found'})
    
    user_id = session.get('user_id')
    user = get_current_user()
    
    # Only registered customers and VIPs can reply
    if user.role not in ['customer', 'vip']:
        return jsonify({'success': False, 'message': 'Only registered customers can reply'})
    
    # Add reply
    reply = {
        'id': f"reply_{datetime.now().timestamp()}",
        'author_id': user_id,
        'author_name': user.username,
        'content': content,
        'created_at': datetime.now().isoformat()
    }
    
    post.replies.append(reply)
    save_forum_post(post)
    
    return jsonify({'success': True, 'message': 'Reply posted successfully'})

@bp.route('/api/v1/nutrition/<dish_id>', methods=['GET'])
def api_nutrition(dish_id):
    """Get or calculate nutritional information for a dish"""
    dish = get_dish_by_id(dish_id)
    if not dish:
        return jsonify({'success': False, 'message': 'Dish not found'}), 404
    
    # If nutrition info already exists, return it
    if dish.nutritional_info:
        return jsonify({
            'success': True,
            'nutritional_info': dish.nutritional_info,
            'cached': True
        })
    
    # Calculate nutrition using AI
    nutrition_info = estimate_nutritional_info(
        dish.name,
        dish.description,
        dish.category
    )
    
    if nutrition_info:
        # Save to dish
        dish.nutritional_info = nutrition_info
        save_dish(dish)
        
        return jsonify({
            'success': True,
            'nutritional_info': nutrition_info,
            'cached': False
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Could not estimate nutritional information at this time'
        }), 500

# ============================================================================
# Manager Routes
# ============================================================================

@bp.route('/manager/dashboard')
@require_login
@require_role('manager')
def manager_dashboard():
    """Manager dashboard"""
    # Get pending registrations
    users = get_all_users()
    pending_users = [u for u in users if u.role in ['customer', 'vip'] and not u.approved]
    
    # Get account closure requests
    closure_requests = [u for u in users if u.role in ['customer', 'vip'] and u.closure_requested]
    
    # Get pending complaints
    from database import get_all_complaints
    complaints = get_all_complaints()
    pending_complaints = [c for c in complaints if c.status in ['pending', 'disputed']]
    
    # Add complainant and target names to complaints
    for complaint in pending_complaints:
        complainant = get_user_by_id(complaint.complainant_id)
        target = get_user_by_id(complaint.target_id)
        complaint.complainant_name = complainant.username if complainant else 'Unknown'
        complaint.target_name = target.username if target else 'Unknown'
    
    # Get all orders for manager view
    orders = get_all_orders()
    pending_orders = [o for o in orders if o.status in ['pending', 'preparing']]
    
    # Add dish names to orders
    dishes = {d.id: d for d in get_all_dishes()}
    for order in orders:
        for item in order.items:
            dish = dishes.get(item.get('dish_id'))
            if dish:
                item['dish_name'] = dish.name
    
    # Get orders ready for delivery with bids
    ready_orders = [o for o in orders if o.status == 'ready' and not o.delivery_person_id]
    orders_with_bids = []
    from database import get_bids_by_order, get_all_delivery_bids
    all_bids = get_all_delivery_bids()
    
    for order in ready_orders:
        # Get all pending bids for this order
        bids = [b for b in all_bids if b.order_id == order.id and b.status == 'pending']
        if bids:
            # Add delivery person names to bids
            for bid in bids:
                delivery_person = get_user_by_id(bid.delivery_person_id)
                bid.delivery_person_name = delivery_person.username if delivery_person else 'Unknown'
            orders_with_bids.append({
                'order': order,
                'bids': sorted(bids, key=lambda b: b.bid_amount)
            })
    
    # Also show orders that are ready but have no bids yet
    orders_without_bids = [o for o in ready_orders if not any(b.order_id == o.id for b in all_bids if b.status == 'pending')]
    
    # Get flagged knowledge base entries
    from database import get_flagged_knowledge_entries
    flagged_kb = get_flagged_knowledge_entries()
    
    # Get pending knowledge base submissions
    from database import get_knowledge_base
    kb_entries = get_knowledge_base()
    pending_kb = [e for e in kb_entries if e.get('author_id') and not e.get('approved', False)]
    
    # Get all employees for HR management
    employees = [u for u in users if u.role in ['chef', 'delivery']]
    
    # Get all users for account management (exclude manager)
    all_users = [u for u in users if u.role != 'manager']
    
    # Get orders with ratings for manager review
    rated_orders = [o for o in orders if o.status == 'delivered' and o.food_rating]
    for order in rated_orders:
        # Add customer name
        customer = get_user_by_id(order.customer_id)
        order.customer_name = customer.username if customer else 'Unknown'
        # Add chef name from dishes
        chef_ids = set()
        for item in order.items:
            dish = dishes.get(item.get('dish_id'))
            if dish and dish.chef_id:
                chef_ids.add(dish.chef_id)
        chef_names = [get_user_by_id(cid).username if get_user_by_id(cid) else 'Unknown' for cid in chef_ids]
        order.chef_names = ', '.join(chef_names) if chef_names else 'Unknown'
    
    return render_template('manager/dashboard.html',
                         pending_users=pending_users,
                         closure_requests=closure_requests,
                         pending_complaints=pending_complaints,
                         pending_orders=pending_orders,
                         orders_with_bids=orders_with_bids,
                         orders_without_bids=orders_without_bids if 'orders_without_bids' in locals() else [],
                         flagged_kb=flagged_kb,
                         pending_kb=pending_kb,
                         employees=employees,
                         all_users=all_users,
                         rated_orders=rated_orders)

@bp.route('/manager/approve/<user_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_approve_user(user_id):
    """Approve user registration"""
    user = get_user_by_id(user_id)
    if user:
        user.approved = True
        save_user(user)
        flash(f'User {user.username} approved', 'success')
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/reject/<user_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_reject_user(user_id):
    """Reject user registration"""
    user = get_user_by_id(user_id)
    if user:
        delete_user(user_id)
        flash(f'User {user.username} rejected', 'info')
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/complaint/resolve/<complaint_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_resolve_complaint(complaint_id):
    """Resolve a complaint"""
    resolution = request.form.get('resolution')  # 'carry_out' or 'overrule'
    manager_id = session.get('user_id')
    
    # Map new resolution types to old ones for backward compatibility
    if resolution == 'carry_out':
        resolution = 'upheld'
    elif resolution == 'overrule':
        resolution = 'dismissed'
    
    success, message = resolve_complaint(complaint_id, manager_id, resolution)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/account/manage', methods=['POST'])
@require_login
@require_role('manager')
def manager_manage_account():
    """Manage user account"""
    data = request.get_json()
    user_id = data.get('user_id')
    action = data.get('action')
    
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    if action == 'approve':
        user.approved = True
        save_user(user)
        return jsonify({'success': True, 'message': f'Account for {user.username} approved'})
    
    elif action == 'hire':
        role = data.get('role')
        salary = float(data.get('amount', 0))
        
        if role not in ['chef', 'delivery']:
            return jsonify({'success': False, 'message': 'Invalid role'})
        
        # Check if we can hire (max 2 per role)
        all_users = get_all_users()
        active_employees = [u for u in all_users if u.role == role and u.approved]
        if len(active_employees) >= 2:
            return jsonify({'success': False, 'message': f'Maximum 2 active {role}s already hired'})
        
        user.role = role
        user.approved = True
        user.salary = salary
        save_user(user)
        return jsonify({'success': True, 'message': f'{user.username} hired as {role}'})
    
    elif action == 'blacklist':
        user.blacklisted = True
        save_user(user)
        return jsonify({'success': True, 'message': f'{user.username} blacklisted'})
    
    elif action == 'unblacklist':
        user.blacklisted = False
        # Clear all warnings
        user.warnings = 0
        # Clear VIP status if they had it (fresh start)
        if user.role == 'vip':
            user.vip_since = None
            user.free_deliveries_used = 0
            user.free_deliveries_earned = 0
        # Make them a fresh customer (not visitor)
        user.role = 'customer'
        # Ensure they're approved as a fresh customer
        user.approved = True
        save_user(user)
        return jsonify({'success': True, 'message': f'Blacklist removed for {user.username}. Warnings cleared and account restored as fresh customer.'})
    
    elif action == 'close':
        blacklist = data.get('blacklist', False)
        refund_balance = data.get('refund_balance', False)
        
        # Refund balance if requested
        if refund_balance and user.balance > 0:
            # In a real system, you'd process the refund here
            user.balance = 0  # For now, just zero it out
        
        user.approved = False
        user.closure_requested = False  # Clear closure request flag
        if blacklist:
            user.blacklisted = True
        save_user(user)
        return jsonify({'success': True, 'message': f'Account for {user.username} closed'})
    
    elif action == 'approve_closure':
        blacklist = data.get('blacklist', False)
        refund_amount = user.balance
        
        # Refund balance
        user.balance = 0.0
        
        # Close account
        user.approved = False
        user.role = 'visitor'
        user.closure_requested = False  # Clear closure request flag
        
        if blacklist:
            user.blacklisted = True
        
        save_user(user)
        
        message = f'Account closure approved. Refunded ${refund_amount:.2f}.'
        if blacklist:
            message += ' User has been blacklisted.'
        
        return jsonify({'success': True, 'message': message})
    
    elif action == 'deny_closure':
        user.closure_requested = False  # Clear closure request flag
        save_user(user)
        return jsonify({'success': True, 'message': f'Account closure request denied for {user.username}'})
    
    return jsonify({'success': False, 'message': 'Invalid action'})

@bp.route('/manager/knowledge/approve/<entry_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_approve_knowledge(entry_id):
    """Approve a knowledge base entry or unflag a flagged entry"""
    from database import get_knowledge_base, save_json, KNOWLEDGE_BASE_FILE, load_json
    entries = get_knowledge_base()
    user_entries = load_json(KNOWLEDGE_BASE_FILE, [])
    
    # Find and update the entry
    found = False
    for i, entry in enumerate(user_entries):
        if entry.get('id') == entry_id:
            entry['approved'] = True
            entry['flagged'] = False
            # Remove flagged metadata
            entry.pop('flagged_by', None)
            entry.pop('flagged_at', None)
            user_entries[i] = entry
            save_json(KNOWLEDGE_BASE_FILE, user_entries)
            flash('Knowledge entry approved/unflagged', 'success')
            found = True
            break
    
    if not found:
        flash('Entry not found', 'error')
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/knowledge/remove/<entry_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_remove_knowledge(entry_id):
    """Remove a knowledge base entry"""
    from database import delete_knowledge_entry, get_knowledge_base
    
    # Get entry to verify it exists
    entries = get_knowledge_base()
    entry = next((e for e in entries if e.get('id') == entry_id), None)
    
    if entry:
        # Remove entry from JSON file
        delete_knowledge_entry(entry_id)
        flash('Knowledge base entry removed successfully', 'success')
    else:
        flash('Entry not found', 'error')
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/knowledge/add', methods=['POST'])
@require_login
@require_role('manager')
def manager_add_knowledge():
    """Add a new knowledge base entry (manager only)"""
    question = request.form.get('question', '').strip()
    answer = request.form.get('answer', '').strip()
    tags_str = request.form.get('tags', '').strip()
    
    if not question or not answer:
        flash('Question and answer are required', 'error')
        return redirect(url_for('main.manager_dashboard'))
    
    # Parse tags (comma-separated)
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
    
    from database import save_knowledge_entry
    save_knowledge_entry({
        'question': question,
        'answer': answer,
        'tags': tags,
        'author_id': session.get('user_id'),
        'approved': True,  # Manager entries are auto-approved
        'is_manager_entry': True
    })
    
    flash('Knowledge base entry added successfully', 'success')
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/delivery/accept', methods=['POST'])
@require_login
@require_role('manager')
def manager_accept_bid():
    """Accept a delivery bid"""
    try:
        order_id = request.form.get('order_id')
        bid_id = request.form.get('bid_id')
        memo = request.form.get('memo', '').strip()
        
        print(f"DEBUG manager_accept_bid: order_id={order_id}, bid_id={bid_id}, memo={memo}")
        
        if not order_id or not bid_id:
            print(f"ERROR: Missing required information - order_id={order_id}, bid_id={bid_id}")
            flash('Missing required information', 'danger')
            return redirect(url_for('main.manager_dashboard'))
        
        manager_id = session.get('user_id')
        print(f"DEBUG: Calling accept_delivery_bid with order_id={order_id}, bid_id={bid_id}, manager_id={manager_id}")
        
        success, message = accept_delivery_bid(order_id, bid_id, manager_id, memo)
        
        print(f"DEBUG: accept_delivery_bid returned: success={success}, message={message}")
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('main.manager_dashboard'))
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"EXCEPTION in manager_accept_bid: {error_msg}")
        traceback.print_exc()
        flash(f'Error accepting bid: {error_msg}', 'danger')
        return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/hr/update', methods=['POST'])
@require_login
@require_role('manager')
def manager_hr_update():
    """Update employee salary or status (hire/fire/raise/cut pay)"""
    data = request.get_json()
    employee_id = data.get('employee_id')
    action = data.get('action')  # 'hire', 'fire', 'raise', 'cut', 'set_salary'
    amount = data.get('amount', 0.0)  # For raise/cut/set_salary
    
    if not employee_id or not action:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    employee = get_user_by_id(employee_id)
    if not employee:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # For actions other than 'hire', user must be an employee
    if action != 'hire' and employee.role not in ['chef', 'delivery']:
        return jsonify({'success': False, 'message': 'User is not an employee'})
    
    if action == 'fire':
        # Fire employee
        employee.role = 'customer'
        employee.approved = False
        employee.salary = 0.0
        save_user(employee)
        return jsonify({'success': True, 'message': f'Employee {employee.username} has been fired'})
    
    elif action == 'hire':
        # Hire employee - can hire anyone who is not currently an active employee
        # Check if they're already an active employee
        if employee.role in ['chef', 'delivery'] and employee.approved:
            return jsonify({'success': False, 'message': 'Employee is already active'})
        
        # Get the role to assign
        new_role = data.get('role', employee.role if employee.role in ['chef', 'delivery'] else 'chef')
        if new_role not in ['chef', 'delivery']:
            new_role = 'chef'  # Default to chef
        
        # Check if we already have 2 of this role
        all_users = get_all_users()
        active_count = len([u for u in all_users if u.role == new_role and u.approved and u.id != employee.id])
        if active_count >= 2:
            return jsonify({'success': False, 'message': f'Already have 2 active {new_role}s. Fire one first or hire as {("delivery" if new_role == "chef" else "chef")}.'})
        
        # Hire the employee
        employee.role = new_role
        employee.approved = True
        # Use provided salary or set default
        if amount > 0:
            employee.salary = amount
        elif employee.salary == 0:
            # Set default salary
            employee.salary = 5000.0 if new_role == 'chef' else 3000.0
        save_user(employee)
        return jsonify({'success': True, 'message': f'Employee {employee.username} has been hired as {new_role} with salary ${employee.salary:.2f}'})
    
    elif action == 'raise':
        # Raise salary by percentage or amount
        if amount > 0:
            if amount <= 1:  # Treat as percentage (0.1 = 10%)
                employee.salary = employee.salary * (1 + amount)
            else:  # Treat as absolute amount
                employee.salary += amount
            save_user(employee)
            return jsonify({'success': True, 'message': f'Salary raised. New salary: ${employee.salary:.2f}'})
    
    elif action == 'cut':
        # Cut salary by percentage or amount
        if amount > 0:
            if amount <= 1:  # Treat as percentage (0.1 = 10%)
                employee.salary = max(0, employee.salary * (1 - amount))
            else:  # Treat as absolute amount
                employee.salary = max(0, employee.salary - amount)
            save_user(employee)
            return jsonify({'success': True, 'message': f'Salary cut. New salary: ${employee.salary:.2f}'})
    
    elif action == 'set_salary':
        # Set absolute salary
        if amount >= 0:
            employee.salary = amount
            save_user(employee)
            return jsonify({'success': True, 'message': f'Salary set to ${employee.salary:.2f}'})
    
    return jsonify({'success': False, 'message': 'Invalid action'})

@bp.route('/manager/account/close', methods=['POST'])
@require_login
@require_role('manager')
def manager_close_account():
    """Close customer account (when kicked out or quits)"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required'})
    
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    if user.role not in ['customer', 'vip', 'visitor']:
        return jsonify({'success': False, 'message': 'Can only close customer accounts'})
    
    # Clear deposit (refund balance)
    refund_amount = user.balance
    user.balance = 0.0
    
    # Close account
    user.approved = False
    user.role = 'visitor'
    
    # Always blacklist when account is closed (kicked out or quit)
    user.blacklisted = True
    
    save_user(user)
    
    message = f'Account closed. Refunded ${refund_amount:.2f}. User has been blacklisted and cannot register again.'
    
    return jsonify({'success': True, 'message': message})

# ============================================================================
# Chef Routes
# ============================================================================

@bp.route('/chef/dashboard')
@require_login
@require_role('chef')
def chef_dashboard():
    """Chef dashboard"""
    user = get_current_user()
    dishes = [d for d in get_all_dishes() if d.chef_id == user.id]
    
    # Get orders that contain dishes made by this chef
    all_orders = get_all_orders()
    my_dish_ids = {d.id for d in dishes}
    chef_orders = []
    
    for order in all_orders:
        # Check if order contains any of this chef's dishes
        for item in order.items:
            if item.get('dish_id') in my_dish_ids:
                chef_orders.append(order)
                break
    
    # Sort orders by status and creation date
    chef_orders.sort(key=lambda x: (
        ['pending', 'preparing', 'ready', 'delivering', 'delivered', 'cancelled'].index(x.status) 
        if x.status in ['pending', 'preparing', 'ready', 'delivering', 'delivered', 'cancelled'] else 999,
        x.created_at
    ))
    
    # Add dish names to orders
    dishes_dict = {d.id: d for d in get_all_dishes()}
    for order in chef_orders:
        for item in order.items:
            dish = dishes_dict.get(item.get('dish_id'))
            if dish:
                item['dish_name'] = dish.name
    
    # Get orders with ratings for this chef's dishes
    rated_orders = [o for o in chef_orders if o.status == 'delivered' and o.food_rating]
    for order in rated_orders:
        # Add customer name
        customer = get_user_by_id(order.customer_id)
        order.customer_name = customer.username if customer else 'Unknown'
    
    return render_template('chef/dashboard.html', dishes=dishes, user=user, orders=chef_orders, rated_orders=rated_orders)

@bp.route('/chef/dish/add', methods=['GET', 'POST'])
@require_login
@require_role('chef')
def chef_add_dish():
    """Add new dish"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        category = request.form.get('category', 'main')
        vip_only = request.form.get('vip_only') == 'on'
        flavor_tags = request.form.getlist('flavor_tags')
        
        if not name or not description or price <= 0:
            flash('Please fill all required fields', 'danger')
            return render_template('chef/add_dish.html')
        
        user = get_current_user()
        
        # Handle image upload
        image_path = '/static/images/default_dish.png'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                saved_path = save_uploaded_image(file, 'dishes')
                if saved_path:
                    image_path = saved_path
        
        dish = Dish(
            name=name,
            description=description,
            price=price,
            chef_id=user.id,
            category=category,
            image=image_path,
            vip_only=vip_only,
            flavor_tags=flavor_tags
        )
        
        save_dish(dish)
        user.dishes_created += 1
        save_user(user)
        
        flash('Dish added successfully', 'success')
        return redirect(url_for('main.chef_dashboard'))
    
    return render_template('chef/add_dish.html')

# ============================================================================
# Delivery Routes
# ============================================================================

@bp.route('/delivery/dashboard')
@require_login
@require_role('delivery')
def delivery_dashboard():
    """Delivery dashboard"""
    user = get_current_user()
    
    # Get available orders
    orders = get_all_orders()
    available_orders = [o for o in orders if o.status == 'ready' and not o.delivery_person_id]
    
    # Get my bids
    from database import get_all_delivery_bids
    bids = get_all_delivery_bids()
    my_bids = [b for b in bids if b.delivery_person_id == user.id]
    
    # Add my bid amount to each available order
    for order in available_orders:
        my_bid = next((b for b in my_bids if b.order_id == order.id and b.status == 'pending'), None)
        order.my_bid = my_bid.bid_amount if my_bid else None
    
    # Get my deliveries with bid memos
    my_deliveries = [o for o in orders if o.delivery_person_id == user.id]
    # Add memo information to deliveries
    for order in my_deliveries:
        # Find the accepted bid for this order
        accepted_bid = next((b for b in bids if b.order_id == order.id and b.delivery_person_id == user.id and b.status == 'accepted'), None)
        if accepted_bid and accepted_bid.manager_memo:
            order.manager_memo = accepted_bid.manager_memo
    
    # Get chefs, delivery persons, and customers for complaint form
    all_users = get_all_users()
    chefs = [u.to_dict() for u in all_users if u.role == 'chef' and u.approved]
    delivery_persons = [u.to_dict() for u in all_users if u.role == 'delivery' and u.approved and u.id != user.id]
    customers = [u.to_dict() for u in all_users if u.role in ['customer', 'vip'] and u.approved]
    
    return render_template('delivery/dashboard.html',
                         available_orders=available_orders,
                         my_bids=my_bids,
                         my_deliveries=my_deliveries,
                         chefs=chefs,
                         delivery_persons=delivery_persons,
                         customers=customers)

@bp.route('/delivery/mark-delivered', methods=['POST'])
@require_login
@require_role('delivery')
def mark_order_delivered():
    """Mark an order as delivered"""
    order_id = request.form.get('order_id')
    user_id = session.get('user_id')
    
    if not order_id:
        flash('Order ID is required', 'danger')
        return redirect(url_for('main.delivery_dashboard'))
    
    order = get_order_by_id(order_id)
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('main.delivery_dashboard'))
    
    # Verify this delivery person is assigned to this order
    if order.delivery_person_id != user_id:
        flash('You are not assigned to this order', 'danger')
        return redirect(url_for('main.delivery_dashboard'))
    
    # Only allow marking as delivered if status is 'delivering'
    if order.status != 'delivering':
        flash(f'Order is already {order.status}', 'warning')
        return redirect(url_for('main.delivery_dashboard'))
    
    # Update order status to delivered
    order.status = 'delivered'
    save_order(order)
    
    flash('Order marked as delivered successfully!', 'success')
    return redirect(url_for('main.delivery_dashboard'))

@bp.route('/api/v1/delivery/bid', methods=['POST'])
@require_login
@require_role('delivery')
def delivery_bid():
    """Submit delivery bid"""
    data = request.get_json()
    order_id = data.get('order_id')
    bid_amount = float(data.get('bid_amount', 0))
    
    if not order_id or bid_amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid bid data'})
    
    user_id = session.get('user_id')
    success, message = submit_delivery_bid(order_id, user_id, bid_amount)
    
    return jsonify({'success': success, 'message': message})

@bp.route('/api/v1/order/update-status', methods=['POST'])
@require_login
def api_update_order_status():
    """Update order status (chef or manager)"""
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    
    if not order_id or not new_status:
        return jsonify({'success': False, 'message': 'Missing order_id or status'})
    
    # Validate status
    valid_statuses = ['pending', 'preparing', 'ready', 'delivering', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status'})
    
    order = get_order_by_id(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'})
    
    user = get_current_user()
    
    # Check permissions
    if user.role == 'chef':
        # Chef can only update orders that contain their dishes
        dishes = get_all_dishes()
        my_dish_ids = {d.id for d in dishes if d.chef_id == user.id}
        order_has_my_dishes = any(item.get('dish_id') in my_dish_ids for item in order.items)
        
        if not order_has_my_dishes:
            return jsonify({'success': False, 'message': 'You can only update orders for your dishes'})
        
        # Chef can only update to: preparing, ready
        if new_status not in ['preparing', 'ready']:
            return jsonify({'success': False, 'message': 'Chefs can only update status to preparing or ready'})
        
        # Validate status transitions
        if order.status == 'pending' and new_status not in ['preparing']:
            return jsonify({'success': False, 'message': 'Can only change from pending to preparing'})
        if order.status == 'preparing' and new_status not in ['ready']:
            return jsonify({'success': False, 'message': 'Can only change from preparing to ready'})
    
    elif user.role == 'manager':
        # Manager can update to any status
        pass
    else:
        return jsonify({'success': False, 'message': 'Only chefs and managers can update order status'})
    
    # Update order status
    order.status = new_status
    save_order(order)
    
    return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})

# ============================================================================
# Developer/Testing Routes
# ============================================================================

