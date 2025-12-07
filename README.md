# AI-Powered Restaurant Order & Delivery System

A Flask-based web application with LLM-powered customer service, food recommendations, and flavor profiling.

## Features

### User Types
- **Visitors**: Browse menus, ask questions, apply for registration
- **Registered Customers**: Order food, rate dishes/delivery, participate in forums
- **VIP Customers**: 5% discount, free delivery (1 per 3 orders), access to special dishes
- **Employees**: 
  - Chefs: Create menus, receive ratings
  - Delivery Personnel: Bid on deliveries, deliver orders
  - Manager: Handle registrations, complaints, HR decisions

### Core Functionality
- **Smart Menu Browsing**: Personalized dish recommendations based on order history
- **AI Customer Service**: Local knowledge base with LLM fallback via chat interface
- **Reputation System**: Complaints, compliments, warnings, and disputes
- **Finance Management**: Deposit-based ordering system
- **HR Management**: Performance-based promotions, demotions, bonuses
- **Delivery Bidding**: Competitive delivery assignment
- **Discussion Forums**: Community interaction around chefs, dishes, delivery

### Creative Features (AI-Powered)
- **Food Recommendations**: Personalized dish suggestions based on preferences and history
- **Flavor Profiling**: Analyze and match dishes to customer taste preferences

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd restaurant-order-system
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (optional):
```bash
cp .env.example .env  # Edit with your settings
```

5. Initialize the system:
```bash
python app.py --init
```

### LLM Setup

This system uses free LLMs from Ollama or HuggingFace. Choose one:

**Option 1: Ollama (Recommended for local deployment)**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama2  # or mistral, phi, etc.
```

**Option 2: HuggingFace**
- Get a free API token from https://huggingface.co
- Set in `.env`: `HUGGINGFACE_TOKEN=your_token_here`
- Or edit `config.py` directly

## Usage

### Starting the Web Application
```bash
python app.py
```

The application will be available at: **http://localhost:5000**

### Default Accounts

**Manager:**
- Username: `manager`
- Password: `admin123`
- Dashboard: `/manager/dashboard`

**Chefs:**
- Username: `chef1` / `chef2`
- Password: `chef123`
- Dashboard: `/chef/dashboard`

**Delivery Personnel:**
- Username: `delivery1` / `delivery2`
- Password: `delivery123`
- Dashboard: `/delivery/dashboard`

**Test Customer:**
- Username: `customer1`
- Password: `customer123`

### First-Time Visitors
1. Visit the homepage at `http://localhost:5000`
2. Browse the menu as a visitor
3. Click "Register" to create an account
4. Wait for manager approval
5. Login with approved credentials

## System Rules

### Customer Progression
- **New → Registered**: Manager approval required
- **Registered → VIP**: Spend $100+ OR make 3 orders without complaints
- **VIP Benefits**: 5% discount, 1 free delivery per 3 orders, special dishes access
- **Warnings**: 3 warnings = deregistration, blacklisted forever

### Employee Performance
- **Chefs**: 
  - Low ratings (<2) or 3 complaints = demotion (lower salary)
  - 2 demotions = fired
  - High ratings (>4) or 3 compliments = bonus
- **Delivery Personnel**: Same rules as chefs
- **Compliments**: Cancel out complaints (1:1 ratio)

### Financial Rules
- All orders require sufficient deposit
- Insufficient funds = order rejected + 1 warning
- Kicked-out customers receive full deposit refund

### Reputation System
- Customers can rate food (1-5 stars) and delivery (1-5 stars) separately
- File complaints/compliments on chefs, delivery personnel, or other customers
- Disputed complaints reviewed by manager
- False complaints = 1 warning to complainant

## Project Structure

```
restaurant-order-system/
├── app.py                  # Flask application entry point
├── routes.py               # All URL routes and endpoints
├── models.py               # Data models (User, Dish, Order, etc.)
├── database.py             # JSON storage operations
├── auth.py                 # Authentication & session management
├── services.py             # Business logic
├── ai_service.py           # LLM integration & creative features
├── utils.py                # Helper functions
├── config.py               # Configuration settings
├── data/                   # JSON data files
├── static/                 # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── images/
└── templates/              # HTML templates (Jinja2)
    ├── base.html
    ├── index.html
    ├── menu.html
    ├── manager/
    ├── chef/
    └── delivery/
```

## Key Web Pages

- `/` - Home page with featured dishes
- `/menu` - Browse all dishes
- `/login` - Login page
- `/register` - Registration for new customers
- `/profile` - Customer profile and order history
- `/order/<dish_id>` - Place an order
- `/cart` - Shopping cart
- `/forum` - Discussion forums
- `/chat` - AI customer service chat
- `/manager/dashboard` - Manager control panel
- `/chef/dashboard` - Chef menu management
- `/delivery/dashboard` - Delivery bidding interface

## API Endpoints (AJAX)

- `POST /api/v1/chat` - Send chat message to AI
- `GET /api/v1/recommendations` - Get personalized dish recommendations
- `POST /api/v1/order` - Place an order
- `POST /api/v1/rating` - Submit rating
- `GET /api/v1/menu/search` - Search dishes
- `POST /api/v1/complaint` - File complaint/compliment

## Development

### Running in Development Mode
```bash
# Enable debug mode in config.py
DEBUG_MODE = True

# Run with auto-reload
python app.py
```

### Adding New Dishes
1. Login as manager or chef
2. Navigate to chef dashboard
3. Click "Add New Dish"
4. Upload image, set price, add description and flavor tags
5. Dish appears on menu immediately

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Reset Database
```bash
python app.py --reset
```

## Deployment

### Local Network Access
Change in `config.py`:
```python
FlaskConfig.HOST = "0.0.0.0"  # Already set by default
```
Access from other devices: `http://<your-ip>:5000`

### Production Deployment

**Using Gunicorn (Linux/Mac):**
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**Using Waitress (Windows):**
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

**Popular Hosting Options:**
- **Heroku**: Easy deployment with free tier
- **PythonAnywhere**: Python-specific hosting
- **DigitalOcean**: VPS with full control
- **AWS/GCP**: Enterprise-grade solutions

## Troubleshooting

### LLM Not Responding
- Check Ollama is running: `ollama list`
- Verify HuggingFace token in config.py
- Check internet connection for HuggingFace API
- Look for errors in terminal/console

### Port Already in Use
```bash
# Change port in config.py
FlaskConfig.PORT = 5001  # or any other available port
```

### Static Files Not Loading
- Check `static/` folder exists
- Verify file paths in templates use `url_for('static', filename='...')`
- Clear browser cache

### Session Issues
```bash
# Clear Flask session files
rm -rf flask_session/
```

## Technologies Used
- **Flask 3.0**: Web framework
- **Jinja2**: Template engine
- **Bootstrap/Tailwind** (optional): CSS framework
- **JavaScript**: Frontend interactivity
- **Ollama/HuggingFace**: LLM integration
- **JSON**: Data storage
- **Pillow**: Image handling
- **bcrypt**: Password security

## Browser Compatibility
- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## License
MIT License - Educational Project

## Contributors
[Your Team Names Here]

## Acknowledgments
- LLM providers: Ollama, HuggingFace
- Course: [Your Course Name]
- Instructor: [Instructor Name]