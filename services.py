"""
Business logic services
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from flask import session
from database import (
    get_user_by_id, save_user, get_all_users,
    get_dish_by_id, get_all_dishes, save_dish,
    get_order_by_id, get_orders_by_customer, save_order, get_all_orders,
    get_ratings_by_entity, save_rating, get_all_ratings,
    get_complaints_by_target, save_complaint, get_all_complaints,
    get_bids_by_order, save_delivery_bid, get_all_delivery_bids
)
from models import Order, Rating, Complaint, DeliveryBid
from config import AppConfig
from utils import calculate_discount, update_user_flavor_profile, calculate_average_rating

def process_order(customer_id: str, items: List[Dict], cart_total: float) -> Tuple[bool, str, Optional[Order]]:
    """
    Process an order
    Returns: (success, message, order)
    """
    customer = get_user_by_id(customer_id)
    if not customer:
        return False, "Customer not found", None
    
    # Check if customer is approved
    if customer.role in ['customer', 'vip'] and not customer.approved:
        return False, "Your account is pending approval", None
    
    # Check for existing warnings that should trigger downgrade/deregistration
    # This handles cases where warnings accumulated before the check was implemented
    customer = check_customer_warnings(customer)
    # Ensure we have the latest customer data
    if not customer:
        customer = get_user_by_id(customer_id)
    
    # Calculate discount for VIP
    discount = calculate_discount(customer, cart_total)
    final_total = cart_total - discount
    
    # Check balance
    if customer.balance < final_total:
        # Add warning
        customer.warnings += 1
        save_user(customer)
        # Check if customer should be downgraded or deregistered
        # This will reload the customer object if downgraded
        customer = check_customer_warnings(customer)
        # Ensure we have the latest customer data
        if not customer:
            customer = get_user_by_id(customer_id)
        if customer and customer.role != 'vip':
            # If downgraded, update the message
            return False, f"Insufficient balance. You need ${final_total:.2f} but have ${customer.balance:.2f}. Warning added. You have been downgraded from VIP to regular customer.", None
        return False, f"Insufficient balance. You need ${final_total:.2f} but have ${customer.balance:.2f}. Warning added.", None
    
    # Award free delivery for VIP customers (1 free delivery per 3 orders)
    free_delivery = False
    if customer.role == 'vip':
        orders_needed = AppConfig.VIP_FREE_DELIVERY_RATIO
        # Award free delivery on every 3rd order (orders 3, 6, 9, etc.)
        if customer.orders_count > 0 and (customer.orders_count + 1) % orders_needed == 0:
            customer.free_deliveries_earned += 1
            # Note: free_delivery flag will be set when delivery bid is accepted if customer has available free deliveries
    
    # Check if customer has free deliveries available for this order (VIP)
    has_free_delivery_available = False
    if customer.role == 'vip':
        available_free_deliveries = customer.free_deliveries_earned - customer.free_deliveries_used
        has_free_delivery_available = available_free_deliveries > 0
    
    # Create order
    order = Order(
        customer_id=customer_id,
        items=items,
        total=final_total,
        discount_applied=discount,
        free_delivery=has_free_delivery_available  # Mark if free delivery is available
    )
    
    # Deduct balance
    customer.balance -= final_total
    customer.total_spent += final_total
    customer.orders_count += 1
    
    # Check for VIP promotion
    if customer.role == 'customer':
        if customer.total_spent >= AppConfig.VIP_SPENDING_THRESHOLD:
            customer.role = 'vip'
            customer.vip_since = datetime.now().isoformat()
        elif customer.orders_count >= AppConfig.VIP_ORDERS_WITHOUT_COMPLAINTS and customer.complaints_count == 0:
            customer.role = 'vip'
            customer.vip_since = datetime.now().isoformat()
    
    save_user(customer)
    save_order(order)
    
    # Update dish order counts
    for item in items:
        dish = get_dish_by_id(item.get('dish_id'))
        if dish:
            dish.orders_count += item.get('quantity', 1)
            save_dish(dish)
    
    return True, "Order placed successfully", order

def submit_rating(order_id: str, user_id: str, dish_id: str, food_rating: int, 
                 delivery_person_id: Optional[str] = None, delivery_rating: Optional[int] = None,
                 comment: str = '') -> Tuple[bool, str]:
    """
    Submit ratings for food and/or delivery
    """
    order = get_order_by_id(order_id)
    if not order or order.customer_id != user_id:
        return False, "Order not found"
    
    if order.food_rating is not None:
        return False, "You have already rated this order"
    
    dish = get_dish_by_id(dish_id)
    if not dish:
        return False, "Dish not found"
    
    # Save food rating
    food_rating_obj = Rating(
        order_id=order_id,
        rated_entity_id=dish_id,
        entity_type='dish',
        rating=food_rating,
        comment=comment,
        user_id=user_id
    )
    save_rating(food_rating_obj)
    
    # Update dish rating
    dish_ratings = [r.rating for r in get_ratings_by_entity(dish_id, 'dish')]
    dish.rating = calculate_average_rating(dish_ratings)
    dish.ratings_count = len(dish_ratings)
    save_dish(dish)
    
    # Update order
    order.food_rating = food_rating
    save_order(order)
    
    # Update user flavor profile
    user = get_user_by_id(user_id)
    if user and dish.flavor_tags:
        update_user_flavor_profile(user, dish.flavor_tags, food_rating)
        save_user(user)
    
    # Save delivery rating if provided
    if delivery_person_id and delivery_rating:
        delivery_rating_obj = Rating(
            order_id=order_id,
            rated_entity_id=delivery_person_id,
            entity_type='delivery',
            rating=delivery_rating,
            user_id=user_id
        )
        save_rating(delivery_rating_obj)
        order.delivery_rating = delivery_rating
        save_order(order)
        
        # Update delivery person rating
        delivery_person = get_user_by_id(delivery_person_id)
        if delivery_person:
            delivery_ratings = [r.rating for r in get_ratings_by_entity(delivery_person_id, 'delivery')]
            delivery_person.rating = calculate_average_rating(delivery_ratings)
            delivery_person.ratings_count = len(delivery_ratings)
            save_user(delivery_person)
    
    return True, "Rating submitted successfully"

def file_complaint(complainant_id: str, target_id: str, target_type: str,
                  complaint_type: str, description: str) -> Tuple[bool, str]:
    """
    File a complaint or compliment
    Can be filed by customers or delivery personnel
    target_id can be a user ID or username
    """
    complainant = get_user_by_id(complainant_id)
    if not complainant:
        return False, "Complainant not found"
    
    # Try to get target by ID first, then by username
    target = get_user_by_id(target_id)
    if not target:
        from database import get_user_by_username
        target = get_user_by_username(target_id)
    
    if not target:
        return False, "Target user not found"
    
    # Allow delivery personnel to complain/compliment customers they delivered to
    if complainant.role == 'delivery' and target_type != 'customer':
        return False, "Delivery personnel can only file complaints/compliments about customers"
    
    if complainant.role not in ['customer', 'vip', 'delivery']:
        return False, "Only customers and delivery personnel can file complaints/compliments"
    
    # Customers can file about chefs, delivery, or other customers
    if complainant.role in ['customer', 'vip'] and target_type not in ['chef', 'delivery', 'customer']:
        return False, "Customers can only file complaints/compliments about chefs, delivery personnel, or other customers"
    
    complaint = Complaint(
        complainant_id=complainant_id,
        target_id=target.id,  # Use target.id to ensure we use the actual user ID
        target_type=target_type,
        complaint_type=complaint_type,
        description=description
    )
    
    save_complaint(complaint)
    
    # Update counts
    # VIP complaints/compliments count twice
    weight = 2 if complainant.role == 'vip' else 1
    
    if complaint_type == 'complaint':
        target.complaints_count += weight
        # Complainant does NOT get a complaint count for filing a complaint
    else:  # compliment
        target.compliments += weight
    
    save_user(target)
    save_user(complainant)
    
    # Compliments cancel out complaints (1:1 ratio)
    if complaint_type == 'compliment' and target.complaints_count > 0:
        # One compliment cancels one complaint
        target.complaints_count = max(0, target.complaints_count - weight)
    
    # Check for demotion/promotion
    check_employee_performance(target)
    
    return True, "Complaint filed successfully"

def check_employee_performance(employee):
    """Check employee performance and apply demotion/promotion"""
    if employee.role not in ['chef', 'delivery']:
        return
    
    # Check for demotion
    low_rating = employee.rating > 0 and employee.rating < AppConfig.LOW_RATING_THRESHOLD
    many_complaints = employee.complaints_count >= AppConfig.COMPLAINTS_FOR_DEMOTION
    
    if low_rating or many_complaints:
        employee.demotions += 1
        employee.salary = max(0, employee.salary * 0.9)  # 10% salary reduction
        
        if employee.demotions >= AppConfig.DEMOTIONS_BEFORE_FIRING:
            # Fire employee (remove from system or mark as inactive)
            employee.role = 'customer'  # Demote to customer
            employee.approved = False
    
    # Check for bonus
    high_rating = employee.rating >= AppConfig.HIGH_RATING_THRESHOLD
    many_compliments = employee.compliments >= AppConfig.COMPLIMENTS_FOR_BONUS
    
    if high_rating or many_compliments:
        employee.bonuses += 1
        employee.salary = employee.salary * 1.1  # 10% salary increase
    
    save_user(employee)

def dispute_complaint(complaint_id: str, user_id: str) -> Tuple[bool, str]:
    """
    Dispute a complaint (by the target user)
    """
    complaints = get_all_complaints()
    complaint = next((c for c in complaints if c.id == complaint_id), None)
    
    if not complaint:
        return False, "Complaint not found"
    
    if complaint.target_id != user_id:
        return False, "You can only dispute complaints filed against you"
    
    if complaint.status != 'pending':
        return False, "Complaint has already been resolved"
    
    complaint.disputed = True
    complaint.status = 'disputed'
    save_complaint(complaint)
    
    return True, "Complaint disputed successfully"

def resolve_complaint(complaint_id: str, manager_id: str, resolution: str) -> Tuple[bool, str]:
    """
    Resolve a complaint (manager only)
    If upheld: target gets warning (if complaint) or benefit (if compliment)
    If dismissed: complainant gets warning for false complaint
    """
    complaints = get_all_complaints()
    complaint = next((c for c in complaints if c.id == complaint_id), None)
    
    if not complaint:
        return False, "Complaint not found"
    
    complaint.status = 'resolved'
    complaint.resolved_by = manager_id
    complaint.resolved_at = datetime.now().isoformat()
    
    if resolution == 'dismissed':  # This is now "overrule"
        # Overrule complaint - originator gets warning (customer/VIP) or complaint (employee)
        # Target gets complaint removed (-1)
        complainant = get_user_by_id(complaint.complainant_id)
        if complainant:
            if complainant.role in ['customer', 'vip']:
                # Customer/VIP gets warning
                complainant.warnings += 1
                save_user(complainant)
                check_customer_warnings(complainant)
            elif complainant.role in ['chef', 'delivery']:
                # Employee gets complaint
                complainant.complaints_count += 1
                save_user(complainant)
                check_employee_performance(complainant)
        complaint.dispute_resolution = 'dismissed'
        
        # Remove the complaint/compliment from target's count since it was overruled
        target = get_user_by_id(complaint.target_id)
        if target:
            if complaint.complaint_type == 'complaint':
                # Remove complaint count (VIP complaints count twice)
                complainant_weight = 2 if complainant and complainant.role == 'vip' else 1
                target.complaints_count = max(0, target.complaints_count - complainant_weight)
            else:  # compliment
                complainant_weight = 2 if complainant and complainant.role == 'vip' else 1
                target.compliments = max(0, target.compliments - complainant_weight)
            save_user(target)
            check_employee_performance(target)  # Recheck performance after removal
        
    elif resolution == 'upheld':
        complaint.dispute_resolution = 'upheld'
        
        # If complaint is upheld, target gets warning (only for complaints, not compliments)
        if complaint.complaint_type == 'complaint':
            target = get_user_by_id(complaint.target_id)
            if target:
                # Only add warning if target is a customer/VIP
                if target.role in ['customer', 'vip']:
                    target.warnings += 1
                    save_user(target)
                    check_customer_warnings(target)
                # For employees, complaints already affect performance via check_employee_performance
    
    save_complaint(complaint)
    return True, "Complaint resolved"

def check_customer_warnings(customer):
    """Check if customer should be deregistered or downgraded"""
    if customer.role in ['customer', 'vip']:
        max_warnings = AppConfig.MAX_WARNINGS_BEFORE_DEREGISTRATION
        if customer.role == 'vip':
            max_warnings = AppConfig.MAX_WARNINGS_FOR_VIP_DOWNGRADE
        
        if customer.warnings >= max_warnings:
            was_vip = customer.role == 'vip'
            if was_vip:
                customer.role = 'customer'
                customer.warnings = 0  # Clear warnings on downgrade
                customer.vip_since = None  # Clear VIP status
            else:
                # Deregister customer and blacklist
                customer.approved = False
                customer.role = 'visitor'
                customer.blacklisted = True
                # Refund balance
                # (In a real system, you'd process the refund)
            
            # Save the changes
            save_user(customer)
            
            # Reload customer to get updated data
            customer = get_user_by_id(customer.id)
            
            # Update session if user is currently logged in
            try:
                if 'user_id' in session and session.get('user_id') == customer.id:
                    session['user'] = customer.to_dict()
                    session['role'] = customer.role
                    session.modified = True
            except RuntimeError:
                # Session not available (e.g., outside request context)
                pass
    
    return customer

def submit_delivery_bid(order_id: str, delivery_person_id: str, bid_amount: float) -> Tuple[bool, str]:
    """
    Submit a delivery bid
    """
    order = get_order_by_id(order_id)
    if not order:
        return False, "Order not found"
    
    if order.status != 'ready':
        return False, "Order is not ready for delivery"
    
    # Check if already has a delivery person
    if order.delivery_person_id:
        return False, "Order already has a delivery person assigned"
    
    # Check if delivery person already bid on this order
    from database import get_all_delivery_bids, save_delivery_bid
    existing_bids = get_all_delivery_bids()
    # Check for any bid by this person for this order (pending or not)
    existing_bid = next((b for b in existing_bids if b.order_id == order_id and b.delivery_person_id == delivery_person_id), None)
    if existing_bid:
        # Update existing bid (reset status to pending if it was rejected)
        existing_bid.bid_amount = bid_amount
        existing_bid.status = 'pending'  # Reset to pending when updating
        save_delivery_bid(existing_bid)
        return True, "Bid updated successfully"
    
    # Create new bid
    bid = DeliveryBid(
        order_id=order_id,
        delivery_person_id=delivery_person_id,
        bid_amount=bid_amount
    )
    
    save_delivery_bid(bid)
    return True, "Bid submitted successfully"

def accept_delivery_bid(order_id: str, bid_id: str, manager_id: str, memo: str = None) -> Tuple[bool, str]:
    """
    Accept a delivery bid (manager or system)
    If choosing a higher bid, memo is required
    """
    print(f"DEBUG accept_delivery_bid: Starting - order_id={order_id}, bid_id={bid_id}, manager_id={manager_id}, memo={memo}")
    
    bids = get_all_delivery_bids()
    print(f"DEBUG: Total bids found: {len(bids)}")
    
    bid = next((b for b in bids if b.id == bid_id and b.order_id == order_id), None)
    
    if not bid:
        print(f"ERROR: Bid not found - bid_id={bid_id}, order_id={order_id}")
        print(f"DEBUG: Available bids: {[(b.id, b.order_id) for b in bids]}")
        return False, "Bid not found"
    
    print(f"DEBUG: Found bid - id={bid.id}, delivery_person_id={bid.delivery_person_id}, status={bid.status}")
    
    order = get_order_by_id(order_id)
    if not order:
        print(f"ERROR: Order not found - order_id={order_id}")
        return False, "Order not found"
    
    print(f"DEBUG: Found order - id={order.id}, status={order.status}, delivery_person_id={order.delivery_person_id}")
    
    # Get ALL bids for this order (not just pending) to find lowest and reject all others
    # Note: get_all_delivery_bids is already imported at the top of the file
    all_order_bids = [b for b in bids if b.order_id == order_id]
    pending_bids = [b for b in all_order_bids if b.status == 'pending']
    lowest_bid = min(pending_bids, key=lambda b: b.bid_amount) if pending_bids else None
    
    if lowest_bid and bid.id != lowest_bid.id and bid.bid_amount > lowest_bid.bid_amount:
        # Choosing higher bid - memo required
        if not memo or not memo.strip():
            return False, "Memo is required when choosing a bid higher than the lowest bid"
        bid.manager_memo = memo.strip()
    
    # Reject ALL other bids for this order (clear all bids)
    for other_bid in all_order_bids:
        if other_bid.id != bid_id:
            other_bid.status = 'rejected'
            try:
                save_delivery_bid(other_bid)
                print(f"DEBUG: Rejected bid {other_bid.id}")
            except Exception as e:
                print(f"ERROR rejecting bid {other_bid.id}: {e}")
    
    # Accept this bid
    bid.status = 'accepted'
    try:
        save_delivery_bid(bid)
        print(f"DEBUG: Accepted bid {bid_id} for order {order_id}, delivery_person_id={bid.delivery_person_id}")
    except Exception as e:
        print(f"ERROR accepting bid: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error saving bid: {str(e)}"
    
    # Check if customer has free delivery available (VIP benefit)
    customer = get_user_by_id(order.customer_id)
    delivery_cost = bid.bid_amount
    free_delivery_applied = False
    
    # Check if order has free_delivery attribute (for backward compatibility)
    order_free_delivery = getattr(order, 'free_delivery', False)
    
    if customer and customer.role == 'vip' and order_free_delivery:
        # Check if customer has available free deliveries
        available_free_deliveries = customer.free_deliveries_earned - customer.free_deliveries_used
        if available_free_deliveries > 0:
            # Apply free delivery - customer doesn't pay delivery cost
            delivery_cost = 0.0
            customer.free_deliveries_used += 1
            free_delivery_applied = True
            save_user(customer)
    
    # Assign to order
    order.delivery_person_id = bid.delivery_person_id
    order.delivery_bid = bid.bid_amount  # Store original bid amount for record keeping
    order.status = 'delivering'
    
    # Update order total and customer balance only if delivery is not free
    if not free_delivery_applied and delivery_cost > 0:
        # Add delivery cost to order total
        order.total += delivery_cost
        # Deduct delivery cost from customer balance
        if customer:
            if customer.balance < delivery_cost:
                # Insufficient balance for delivery - this shouldn't happen as order was already placed
                # But handle it gracefully
                return False, f"Insufficient balance for delivery cost (${delivery_cost:.2f})"
            customer.balance -= delivery_cost
            customer.total_spent += delivery_cost
            save_user(customer)
    
    # Save the order with the assigned delivery person
    try:
        save_order(order)
        print(f"DEBUG: Saved order {order_id} with delivery_person_id={order.delivery_person_id}, status={order.status}")
    except Exception as e:
        print(f"ERROR saving order: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error saving order: {str(e)}"
    
    # Verify the order was saved correctly
    saved_order = get_order_by_id(order_id)
    if not saved_order:
        return False, "Order not found after saving"
    
    if saved_order.delivery_person_id != bid.delivery_person_id:
        print(f"ERROR: Order delivery_person_id mismatch! Expected: {bid.delivery_person_id}, Got: {saved_order.delivery_person_id}")
        return False, f"Failed to assign order to delivery person. Expected {bid.delivery_person_id}, got {saved_order.delivery_person_id}"
    
    print(f"DEBUG: Verified order {order_id} saved correctly with delivery_person_id={saved_order.delivery_person_id}")
    
    message = f"Bid accepted. Order assigned to delivery person {bid.delivery_person_id}"
    if free_delivery_applied:
        message += f". Free delivery applied! (Saved ${bid.bid_amount:.2f})"
    
    return True, message

def get_popular_dishes(limit: int = 6) -> List[Dict]:
    """Get most popular dishes"""
    dishes = get_all_dishes()
    dishes = [d for d in dishes if d.available]
    dishes.sort(key=lambda x: x.orders_count, reverse=True)
    return [d.to_dict() for d in dishes[:limit]]

def get_top_rated_dishes(limit: int = 6) -> List[Dict]:
    """Get top rated dishes"""
    dishes = get_all_dishes()
    dishes = [d for d in dishes if d.available and d.rating > 0]
    dishes.sort(key=lambda x: x.rating, reverse=True)
    return [d.to_dict() for d in dishes[:limit]]

def get_featured_chefs(limit: int = 4) -> List[Dict]:
    """Get featured chefs"""
    users = get_all_users()
    chefs = [u for u in users if u.role == 'chef' and u.rating > 0]
    chefs.sort(key=lambda x: x.rating, reverse=True)
    
    # Chef avatar mapping - using cartoon-style placeholder avatars
    chef_avatars = {
        'chef1': 'https://api.dicebear.com/7.x/avataaars/svg?seed=chef1&backgroundColor=b6e3f4,c0aede,ffd5dc,ffdfbf',
        'chef2': 'https://api.dicebear.com/7.x/avataaars/svg?seed=chef2&backgroundColor=b6e3f4,c0aede,ffd5dc,ffdfbf'
    }
    
    result = []
    for chef in chefs[:limit]:
        dishes = [d for d in get_all_dishes() if d.chef_id == chef.id]
        result.append({
            'id': chef.id,
            'name': chef.username,
            'specialty': chef.specialty or 'General Cuisine',
            'rating': chef.rating,
            'dishes_count': len(dishes),
            'orders_count': sum(d.orders_count for d in dishes),
            'image': chef_avatars.get(chef.id, f'/static/images/chefs/{chef.id}.png')
        })
    
    return result
