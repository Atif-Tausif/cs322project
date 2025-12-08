#!/usr/bin/env python3
"""Check if orders are being assigned to delivery persons correctly"""
from database import get_all_orders, get_all_delivery_bids, get_order_by_id
from models import Order

print("=" * 60)
print("ORDER ASSIGNMENT CHECK")
print("=" * 60)

# Get all orders
orders = get_all_orders()
print(f"\nTotal orders: {len(orders)}")

# Check orders with delivery_person_id
assigned_orders = [o for o in orders if o.delivery_person_id]
print(f"Orders assigned to delivery persons: {len(assigned_orders)}")

if assigned_orders:
    print("\nAssigned orders:")
    for o in assigned_orders:
        print(f"  Order {o.id[:12]}:")
        print(f"    delivery_person_id: {o.delivery_person_id}")
        print(f"    status: {o.status}")
        print(f"    delivery_bid: {o.delivery_bid}")
else:
    print("\nNo orders assigned to delivery persons")

# Check orders without delivery_person_id
unassigned_orders = [o for o in orders if not o.delivery_person_id]
print(f"\nUnassigned orders: {len(unassigned_orders)}")
if unassigned_orders:
    print("\nUnassigned orders:")
    for o in unassigned_orders:
        print(f"  Order {o.id[:12]}: status={o.status}")

# Check bids
print("\n" + "=" * 60)
print("BID STATUS CHECK")
print("=" * 60)

bids = get_all_delivery_bids()
print(f"\nTotal bids: {len(bids)}")

accepted_bids = [b for b in bids if b.status == 'accepted']
print(f"Accepted bids: {len(accepted_bids)}")

if accepted_bids:
    print("\nAccepted bids:")
    for b in accepted_bids:
        print(f"  Bid {b.id[:20]}:")
        print(f"    order_id: {b.order_id[:12]}")
        print(f"    delivery_person_id: {b.delivery_person_id}")
        print(f"    status: {b.status}")
        print(f"    bid_amount: {b.bid_amount}")
        
        # Check if the order is assigned
        order = get_order_by_id(b.order_id)
        if order:
            print(f"    Order delivery_person_id: {order.delivery_person_id}")
            print(f"    Order status: {order.status}")
            if order.delivery_person_id != b.delivery_person_id:
                print(f"    ⚠️  MISMATCH: Order not assigned to bid's delivery person!")
        else:
            print(f"    ⚠️  Order not found!")

pending_bids = [b for b in bids if b.status == 'pending']
print(f"\nPending bids: {len(pending_bids)}")

print("\n" + "=" * 60)

