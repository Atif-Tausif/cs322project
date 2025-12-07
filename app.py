"""
Flask Application Entry Point
"""
import sys
from flask import Flask
from config import FlaskConfig, DATA_DIR
from routes import bp
from database import reset_database, save_user, get_user_by_username
from models import User
from utils import hash_password

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = FlaskConfig.SECRET_KEY
    app.config['DEBUG'] = FlaskConfig.DEBUG_MODE
    
    # Register blueprints
    app.register_blueprint(bp)
    
    return app

def initialize_database():
    """Initialize database with default users and sample data"""
    print("Initializing database...")
    
    # Reset database
    reset_database()
    
    # Create default manager
    if not get_user_by_username('manager'):
        manager = User(
            username='manager',
            password_hash=hash_password('admin123'),
            role='manager',
            email='manager@restaurant.com',
            approved=True,
            balance=0.0
        )
        save_user(manager)
        print("Created manager account: manager / admin123")
    
    # Create default chefs
    for i in range(1, 3):
        username = f'chef{i}'
        if not get_user_by_username(username):
            chef = User(
                username=username,
                password_hash=hash_password('chef123'),
                role='chef',
                email=f'{username}@restaurant.com',
                approved=True,
                salary=5000.0,
                specialty=f'Specialty {i}',
                rating=4.5
            )
            save_user(chef)
            print(f"Created chef account: {username} / chef123")
    
    # Create default delivery personnel
    for i in range(1, 3):
        username = f'delivery{i}'
        if not get_user_by_username(username):
            delivery = User(
                username=username,
                password_hash=hash_password('delivery123'),
                role='delivery',
                email=f'{username}@restaurant.com',
                approved=True,
                salary=3000.0,
                rating=4.0
            )
            save_user(delivery)
            print(f"Created delivery account: {username} / delivery123")
    
    # Create test customer
    if not get_user_by_username('customer1'):
        customer = User(
            username='customer1',
            password_hash=hash_password('customer123'),
            role='customer',
            email='customer1@example.com',
            approved=True,
            balance=100.0
        )
        save_user(customer)
        print("Created test customer: customer1 / customer123")
    
    # Create sample dishes
    from database import save_dish, get_all_dishes
    from models import Dish
    
    if len(get_all_dishes()) == 0:
        chefs = [u for u in [get_user_by_username('chef1'), get_user_by_username('chef2')] if u]
        
        sample_dishes = [
            {
                'name': 'Classic Burger',
                'description': 'Juicy beef patty with lettuce, tomato, and special sauce',
                'price': 12.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Margherita Pizza',
                'description': 'Fresh mozzarella, tomato sauce, and basil',
                'price': 15.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Spicy Chicken Wings',
                'description': 'Crispy wings with hot sauce',
                'price': 10.99,
                'category': 'appetizers',
                'flavor_tags': ['spicy'],
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Chocolate Lava Cake',
                'description': 'Warm chocolate cake with molten center',
                'price': 8.99,
                'category': 'desserts',
                'flavor_tags': ['sweet'],
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'VIP Special Steak',
                'description': 'Premium ribeye steak with truffle butter',
                'price': 35.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'vip_only': True,
                'chef_id': chefs[0].id if chefs else None
            }
        ]
        
        for dish_data in sample_dishes:
            if dish_data['chef_id']:
                dish = Dish(**dish_data)
                save_dish(dish)
        
        print(f"Created {len(sample_dishes)} sample dishes")
    
    print("Database initialization complete!")

if __name__ == '__main__':
    app = create_app()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--init':
            initialize_database()
            sys.exit(0)
        elif sys.argv[1] == '--reset':
            print("Resetting database...")
            reset_database()
            initialize_database()
            sys.exit(0)
    
    # Run app
    print(f"Starting Flask app on {FlaskConfig.HOST}:{FlaskConfig.PORT}")
    print(f"Visit http://localhost:{FlaskConfig.PORT}")
    app.run(
        host=FlaskConfig.HOST,
        port=FlaskConfig.PORT,
        debug=FlaskConfig.DEBUG_MODE
    )
