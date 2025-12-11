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
                'image': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Margherita Pizza',
                'description': 'Fresh mozzarella, tomato sauce, and basil',
                'price': 15.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'image': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Spicy Chicken Wings',
                'description': 'Crispy wings with hot sauce',
                'price': 10.99,
                'category': 'appetizers',
                'flavor_tags': ['spicy'],
                'image': 'https://img.freepik.com/premium-photo/grilled-spicy-chicken-wings-with-ketchup-black-plate-dark-slate-stone-concrete_662214-219187.jpg?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Chocolate Lava Cake',
                'description': 'Warm chocolate cake with molten center',
                'price': 8.99,
                'category': 'desserts',
                'flavor_tags': ['sweet'],
                'image': 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400&h=300&fit=crop',
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'VIP Special Steak',
                'description': 'Premium ribeye steak with truffle butter',
                'price': 35.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'vip_only': True,
                'image': 'https://images.unsplash.com/photo-1600891965053-dc9e460f3a53?auto=format&fit=crop&w=400&h=300&q=80',
                'chef_id': chefs[0].id if chefs else None
            },
            # Additional non-VIP dishes
            {
                'name': 'Caesar Salad',
                'description': 'Fresh romaine lettuce with Caesar dressing, croutons, and parmesan',
                'price': 9.99,
                'category': 'appetizers',
                'flavor_tags': ['savory', 'tangy'],
                'image': 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Grilled Salmon',
                'description': 'Fresh Atlantic salmon with lemon butter sauce and seasonal vegetables',
                'price': 18.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'image': 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400&h=300&fit=crop',
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'French Onion Soup',
                'description': 'Classic French onion soup with melted Gruyère cheese',
                'price': 7.99,
                'category': 'appetizers',
                'flavor_tags': ['savory'],
                'image': 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Pasta Carbonara',
                'description': 'Creamy pasta with bacon, eggs, and parmesan cheese',
                'price': 14.99,
                'category': 'main',
                'flavor_tags': ['savory'],
                'image': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=400&h=300&fit=crop',
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'New York Cheesecake',
                'description': 'Rich and creamy classic New York style cheesecake with berry compote',
                'price': 7.99,
                'category': 'desserts',
                'flavor_tags': ['sweet'],
                'image': 'https://images.unsplash.com/photo-1524351199678-941a58a3df50?w=400&h=300&fit=crop',
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'Tiramisu',
                'description': 'Classic Italian dessert with coffee-soaked ladyfingers and mascarpone',
                'price': 8.99,
                'category': 'desserts',
                'flavor_tags': ['sweet'],
                'image': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&h=300&fit=crop',
                'chef_id': chefs[1].id if len(chefs) > 1 else chefs[0].id if chefs else None
            },
            {
                'name': 'Apple Pie',
                'description': 'Homemade apple pie with cinnamon and a flaky crust, served with vanilla ice cream',
                'price': 6.99,
                'category': 'desserts',
                'flavor_tags': ['sweet'],
                'image': 'https://images.unsplash.com/photo-1621303837174-89787a7d4729?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Iced Coffee',
                'description': 'Chilled coffee with ice, served with cream and sugar on the side',
                'price': 4.99,
                'category': 'beverages',
                'flavor_tags': [],
                'image': 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Fresh Lemonade',
                'description': 'Freshly squeezed lemonade with a hint of mint',
                'price': 3.99,
                'category': 'beverages',
                'flavor_tags': ['tangy', 'sweet'],
                'image': 'https://images.unsplash.com/photo-1497534446932-c925b458314e?auto=format&fit=crop&w=400&h=300&q=80',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'Orange Juice',
                'description': 'Freshly squeezed orange juice, served cold',
                'price': 3.49,
                'category': 'beverages',
                'flavor_tags': ['tangy', 'sweet'],
                'image': 'https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=400&h=300&q=80',
                'chef_id': chefs[0].id if chefs else None
            },
            {
                'name': 'BBQ Ribs',
                'description': 'Slow-cooked pork ribs with our signature BBQ sauce',
                'price': 19.99,
                'category': 'main',
                'flavor_tags': ['savory', 'spicy'],
                'image': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=300&fit=crop',
                'chef_id': chefs[0].id if chefs else None
            }
        ]
        
        for dish_data in sample_dishes:
            if dish_data['chef_id']:
                dish = Dish(**dish_data)
                save_dish(dish)
        
        print(f"Created {len(sample_dishes)} sample dishes")
    
    # Initialize knowledge base with default entries
    from database import save_json, KNOWLEDGE_BASE_FILE
    knowledge_base_entries = [
        {
            "id": "kb_1",
            "question": "What are your hours?",
            "answer": "We're open Monday through Sunday from 11:00 AM to 10:00 PM.",
            "tags": ["hours", "time", "open"],
            "approved": True,
            "is_manager_entry": True
        },
        {
            "id": "kb_2",
            "question": "Do you offer delivery?",
            "answer": "Yes! We offer delivery service. VIP members get 1 free delivery per 3 orders.",
            "tags": ["delivery", "shipping"],
            "approved": True,
            "is_manager_entry": True
        },
        {
            "id": "kb_4",
            "question": "What payment methods do you accept?",
            "answer": "We use a deposit-based system. You need to maintain a balance in your account to place orders.",
            "tags": ["payment", "deposit", "balance"],
            "approved": True,
            "is_manager_entry": True
        },
        {
            "id": "kb_5",
            "question": "Can I cancel my order?",
            "answer": "Please contact our customer service through the chat if you need to cancel an order. Cancellation policies may vary based on order status.",
            "tags": ["cancel", "order", "refund"],
            "approved": True,
            "is_manager_entry": True
        },
        {
            "id": "kb_6",
            "question": "How do I rate a dish?",
            "answer": "After receiving your order, you can rate both the food (1-5 stars) and delivery service (1-5 stars) separately on your order history page.",
            "tags": ["rating", "review", "feedback"],
            "approved": True,
            "is_manager_entry": True
        },
        {
            "question": "Hello",
            "answer": "Hi",
            "tags": ["a"],
            "author_id": "customer1",
            "approved": False,
            "id": "kb_-3364931573902036106"
        }
    ]
    
    # Initialize knowledge base (will overwrite if reset was called)
    save_json(KNOWLEDGE_BASE_FILE, knowledge_base_entries)
    print(f"Initialized knowledge base with {len(knowledge_base_entries)} entries")
    
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
