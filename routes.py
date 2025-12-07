"""
Flask routes and endpoints
"""
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
from ai_service import get_ai_response, get_personalized_recommendations, get_flavor_profile_analysis
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
    chefs = [u for u in get_all_users() if u.role == 'chef']
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
        
        # Check if user is blacklisted
        all_users = get_all_users()
        blacklisted_user = next((u for u in all_users if u.username == username and u.blacklisted), None)
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
    
    return render_template('profile.html', user=user, orders=orders[:10], 
                         flavor_analysis=flavor_analysis, my_complaints=my_complaints)

@bp.route('/orders')
@require_login
@require_approved
def orders():
    """Order history page"""
    user = get_current_user()
    orders = get_orders_by_customer(user.id)
    
    # Add dish names and prices to orders
    dishes = {d.id: d for d in get_all_dishes()}
    for order in orders:
        for item in order.items:
            dish = dishes.get(item.get('dish_id'))
            if dish:
                item['dish_name'] = dish.name
                item['dish_image'] = dish.image
                # Use stored price if available, otherwise get current price
                item['price'] = item.get('price', dish.price)
    
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
    
    return render_template('forum.html', posts=posts)

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
    flavor = request.args.get('flavor')
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
        
        # Flavor filter (VIP only)
        if flavor and dish.flavor_tags and flavor not in dish.flavor_tags:
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
    
    # Add chef names
    chefs = {u.id: u.username for u in get_all_users() if u.role == 'chef'}
    dishes_dict = []
    for dish in paginated:
        dish_dict = dish.to_dict()
        dish_dict['chef_name'] = chefs.get(dish.chef_id, 'Unknown')
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
    
    if not items:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
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
    success, message, order = process_order(user_id, items, total)
    
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
    food_rating = int(data.get('food_rating', 0))
    delivery_rating = data.get('delivery_rating')
    delivery_person_id = data.get('delivery_person_id')
    comment = data.get('comment', '')
    
    if not order_id or not dish_id or not (1 <= food_rating <= 5):
        return jsonify({'success': False, 'message': 'Invalid rating data'})
    
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
    
    # Delivery personnel can only complain about customers
    if user.role == 'delivery' and target_type != 'customer':
        return jsonify({'success': False, 'message': 'Delivery personnel can only file complaints about customers'})
    
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
    
    # Get pending complaints
    from database import get_all_complaints
    complaints = get_all_complaints()
    pending_complaints = [c for c in complaints if c.status in ['pending', 'disputed']]
    
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
    ready_orders = [o for o in orders if o.status == 'ready']
    orders_with_bids = []
    from database import get_bids_by_order
    for order in ready_orders:
        bids = get_bids_by_order(order.id)
        if bids:
            # Add delivery person names to bids
            for bid in bids:
                delivery_person = get_user_by_id(bid.delivery_person_id)
                bid.delivery_person_name = delivery_person.username if delivery_person else 'Unknown'
            orders_with_bids.append({
                'order': order,
                'bids': sorted(bids, key=lambda b: b.bid_amount)
            })
    
    # Get flagged knowledge base entries
    from database import get_flagged_knowledge_entries
    flagged_kb = get_flagged_knowledge_entries()
    
    # Get pending knowledge base submissions
    from database import get_knowledge_base
    kb_entries = get_knowledge_base()
    pending_kb = [e for e in kb_entries if e.get('author_id') and not e.get('approved', False)]
    
    return render_template('manager/dashboard.html',
                         pending_users=pending_users,
                         pending_complaints=pending_complaints,
                         pending_orders=pending_orders,
                         orders_with_bids=orders_with_bids,
                         flagged_kb=flagged_kb,
                         pending_kb=pending_kb)

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
    resolution = request.form.get('resolution')  # 'upheld' or 'dismissed'
    manager_id = session.get('user_id')
    
    success, message = resolve_complaint(complaint_id, manager_id, resolution)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/knowledge/approve/<entry_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_approve_knowledge(entry_id):
    """Approve a knowledge base entry"""
    from database import get_knowledge_base, save_json, KNOWLEDGE_BASE_FILE, load_json
    entries = get_knowledge_base()
    user_entries = load_json(KNOWLEDGE_BASE_FILE, [])
    
    for entry in user_entries:
        if entry.get('id') == entry_id:
            entry['approved'] = True
            entry['flagged'] = False
            save_json(KNOWLEDGE_BASE_FILE, user_entries)
            flash('Knowledge entry approved', 'success')
            break
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/knowledge/remove/<entry_id>', methods=['POST'])
@require_login
@require_role('manager')
def manager_remove_knowledge(entry_id):
    """Remove a bad knowledge base entry and ban author"""
    from database import delete_knowledge_entry, get_knowledge_base, get_user_by_id, save_user
    from database import load_json, save_json, KNOWLEDGE_BASE_FILE
    
    # Get entry to find author
    entries = get_knowledge_base()
    entry = next((e for e in entries if e.get('id') == entry_id), None)
    
    if entry and entry.get('author_id'):
        # Ban author from contributing
        author = get_user_by_id(entry['author_id'])
        if author:
            author.blacklisted = True
            save_user(author)
            flash(f'Entry removed and author {author.username} banned from contributing', 'info')
    
    # Remove entry
    delete_knowledge_entry(entry_id)
    
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/delivery/accept', methods=['POST'])
@require_login
@require_role('manager')
def manager_accept_bid():
    """Accept a delivery bid"""
    order_id = request.form.get('order_id')
    bid_id = request.form.get('bid_id')
    memo = request.form.get('memo', '').strip()
    
    manager_id = session.get('user_id')
    success, message = accept_delivery_bid(order_id, bid_id, manager_id, memo)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('main.manager_dashboard'))

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
    
    return render_template('chef/dashboard.html', dishes=dishes, user=user, orders=chef_orders)

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
    available_orders = [o for o in orders if o.status == 'ready']
    
    # Get my bids
    from database import get_all_delivery_bids
    bids = get_all_delivery_bids()
    my_bids = [b for b in bids if b.delivery_person_id == user.id]
    
    # Get my deliveries
    my_deliveries = [o for o in orders if o.delivery_person_id == user.id]
    
    return render_template('delivery/dashboard.html',
                         available_orders=available_orders,
                         my_bids=my_bids,
                         my_deliveries=my_deliveries)

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
