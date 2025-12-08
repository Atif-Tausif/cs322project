"""
Test balance update functionality
"""
from database import get_user_by_username, save_user, get_all_users
from models import User

def test_balance_update():
    print("Testing balance update...")
    
    # Get customer1
    user = get_user_by_username('customer1')
    if not user:
        print("❌ customer1 not found")
        return
    
    print(f"Current balance: ${user.balance}")
    
    # Update balance
    old_balance = user.balance
    user.balance = 100.50
    save_user(user)
    
    # Verify it saved
    user_reloaded = get_user_by_username('customer1')
    print(f"New balance: ${user_reloaded.balance}")
    
    if user_reloaded.balance == 100.50:
        print("✅ Balance update works!")
    else:
        print("❌ Balance update failed!")
        print(f"Expected: 100.50, Got: {user_reloaded.balance}")

if __name__ == "__main__":
    test_balance_update()