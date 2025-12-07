"""
Business logic services
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
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
    
    # Calculate discount for VIP
    discount = calculate_discount(customer, cart_total)
    final_total = cart_total - discount
    
    # Check balance
    if customer.balance < final_total:
        # Add warning
        customer.warnings += 1
        save_user(customer)
        return False, f"Insufficient balance. You need ${final_total:.2f} but have ${customer.balance:.2f}. Warning added.", None
    
    # Check if customer has free delivery (VIP)
    free_delivery = False
    if customer.role == 'vip':
        orders_needed = AppConfig.VIP_FREE_DELIVERY_RATIO
        if customer.orders_count > 0 and (customer.orders_count + 1) % orders_needed == 0:
            free_delivery = True
            customer.free_deliveries_earned += 1
    
    # Create order
    order = Order(
        customer_id=customer_id,
        items=items,
        total=final_total,
        discount_applied=discount,
        free_delivery=free_delivery
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
    """
    complainant = get_user_by_id(complainant_id)
    target = get_user_by_id(target_id)
    
    if not complainant or not target:
        return False, "User not found"
    
    # Allow delivery personnel to complain/compliment customers they delivered to
    if complainant.role == 'delivery' and target_type != 'customer':
        return False, "Delivery personnel can only file complaints/compliments about customers"
    
    if complainant.role not in ['customer', 'vip', 'delivery']:
        return False, "Only customers and delivery personnel can file complaints/compliments"
    
    complaint = Complaint(
        complainant_id=complainant_id,
        target_id=target_id,
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
        complainant.complaints_count += 1
    else:  # compliment
        target.compliments += weight
    
    save_user(target)
    save_user(complainant)
    
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
    """
    complaints = get_all_complaints()
    complaint = next((c for c in complaints if c.id == complaint_id), None)
    
    if not complaint:
        return False, "Complaint not found"
    
    complaint.status = 'resolved'
    complaint.resolved_by = manager_id
    complaint.resolved_at = datetime.now().isoformat()
    
    if resolution == 'dismissed':
        # False complaint - warn complainant
        complainant = get_user_by_id(complaint.complainant_id)
        if complainant:
            complainant.warnings += 1
            save_user(complainant)
            check_customer_warnings(complainant)
        complaint.dispute_resolution = 'dismissed'
    elif resolution == 'upheld':
        complaint.dispute_resolution = 'upheld'
    
    save_complaint(complaint)
    return True, "Complaint resolved"

def check_customer_warnings(customer):
    """Check if customer should be deregistered"""
    if customer.role in ['customer', 'vip']:
        max_warnings = AppConfig.MAX_WARNINGS_BEFORE_DEREGISTRATION
        if customer.role == 'vip':
            max_warnings = AppConfig.MAX_WARNINGS_FOR_VIP_DOWNGRADE
        
        if customer.warnings >= max_warnings:
            if customer.role == 'vip':
                customer.role = 'customer'
                customer.warnings = 0  # Clear warnings on downgrade
            else:
                # Deregister customer and blacklist
                customer.approved = False
                customer.role = 'visitor'
                customer.blacklisted = True
                # Refund balance
                # (In a real system, you'd process the refund)
            save_user(customer)

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
    bids = get_all_delivery_bids()
    bid = next((b for b in bids if b.id == bid_id and b.order_id == order_id), None)
    
    if not bid:
        return False, "Bid not found"
    
    order = get_order_by_id(order_id)
    if not order:
        return False, "Order not found"
    
    # Check if this is not the lowest bid
    all_bids = get_bids_by_order(order_id)
    lowest_bid = min(all_bids, key=lambda b: b.bid_amount) if all_bids else None
    
    if lowest_bid and bid.id != lowest_bid.id and bid.bid_amount > lowest_bid.bid_amount:
        # Choosing higher bid - memo required
        if not memo or not memo.strip():
            return False, "Memo is required when choosing a bid higher than the lowest bid"
        bid.manager_memo = memo.strip()
    
    # Reject other bids
    for other_bid in all_bids:
        if other_bid.id != bid_id:
            other_bid.status = 'rejected'
            save_delivery_bid(other_bid)
    
    # Accept this bid
    bid.status = 'accepted'
    save_delivery_bid(bid)
    
    # Assign to order
    order.delivery_person_id = bid.delivery_person_id
    order.delivery_bid = bid.bid_amount
    order.status = 'delivering'
    save_order(order)
    
    return True, "Bid accepted"

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
            'image': f'/static/images/chefs/{chef.id}.png'
        })
    
    return result
