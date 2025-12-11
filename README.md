# AI-Powered Restaurant Order & Delivery System

A comprehensive Flask-based web application featuring AI-powered customer service, personalized food recommendations, intelligent flavor profiling, and a complete restaurant management system.

## Features

### User Roles
- **Visitors**: Browse menus, interact with AI chat, apply for registration
- **Registered Customers**: Order food, rate dishes/delivery, participate in forums
- **VIP Customers**: 5% discount, free delivery (1 per 3 orders), access to exclusive dishes
- **Chefs**: Create and manage menu items, receive ratings and feedback
- **Delivery Personnel**: Bid on deliveries, track delivery status
- **Manager**: Handle registrations, complaints, HR decisions, knowledge base management

### Core Functionality
- **Smart Menu Browsing**: Personalized dish recommendations based on order history and flavor preferences
- **AI Customer Service**: Local knowledge base with LLM fallback via interactive chat interface
- **Reputation System**: Complaints, compliments, warnings, and dispute resolution
- **Finance Management**: Deposit-based ordering system with balance tracking
- **HR Management**: Performance-based promotions, demotions, and bonuses
- **Delivery Bidding**: Competitive delivery assignment system
- **Discussion Forums**: Community interaction around chefs, dishes, and delivery experiences
- **AI Meal Planner**: Generate complete meal plans based on preferences and budget

### AI-Powered Features
- **Food Recommendations**: Personalized dish suggestions based on preferences and order history
- **Flavor Profiling**: Analyze and match dishes to customer taste preferences
- **Intelligent Chat**: AI-powered customer service with knowledge base integration
- **Meal Plan Generator**: AI suggests appetizer + main + dessert combinations

## Prerequisites

- **Python 3.8 or higher**
- **pip** package manager
- **One of the following AI providers:**
  - Google Gemini API (recommended for cloud/remote access)
  - Ollama (recommended for local development)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd cs322project
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up AI Provider

Choose one of the following options:

#### Option 1: Google Gemini (Recommended for Cloud/Remote Access)

**Advantages:**
- No local installation required
- Works on any device with internet
- Fast and reliable
- Free tier available

**Setup Steps:**

1. **Get a Gemini API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy your API key

2. **Set Environment Variable:**

   **Windows (Command Prompt):**
   ```cmd
   set GEMINI_API_KEY=your_api_key_here
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:GEMINI_API_KEY="your_api_key_here"
   ```

   **Linux/Mac:**
   ```bash
   export GEMINI_API_KEY=your_api_key_here
   ```

   **Or create a `.env` file** in the project root:
   ```
   GEMINI_API_KEY=your_api_key_here
   LLM_PROVIDER=gemini
   ```

3. **Verify Setup:**
   - The system automatically uses Gemini if `GEMINI_API_KEY` is set
   - Default model: `gemini-2.5-flash` (can be changed via `GEMINI_MODEL` environment variable)

#### Option 2: Ollama (Recommended for Local Development)

**Advantages:**
- Runs completely locally
- No API keys required
- Works offline
- Full control over models

**Setup Steps:**

1. **Install Ollama:**
   - Visit [https://ollama.ai](https://ollama.ai)
   - Download and install Ollama for your operating system
   - The Ollama service starts automatically after installation

2. **Download a Model:**
   ```bash
   # Recommended models (choose one):
   ollama pull llama3          # Fast and efficient (recommended)
   ollama pull mistral         # Good balance of speed and quality
   ollama pull phi3            # Lightweight option
   ```

3. **Verify Installation:**
   ```bash
   # Check if Ollama is running
   ollama list
   # Should show your installed models
   ```

4. **Configure (Optional):**
   - Default model: `llama3`
   - Default URL: `http://localhost:11434`
   - To use a different model: `export OLLAMA_MODEL=your_model_name`
   - To use a different URL: `export OLLAMA_BASE_URL=http://your-ollama-url:11434`

5. **Set Provider (if not using Gemini):**
   ```bash
   # Set environment variable
   export LLM_PROVIDER=ollama  # Linux/Mac
   set LLM_PROVIDER=ollama     # Windows CMD
   $env:LLM_PROVIDER="ollama"   # Windows PowerShell
   ```

### Step 5: Initialize the Database

```bash
python app.py --init
```

This creates:
- Default user accounts (manager, chefs, delivery personnel, test customer)
- Sample dishes with images
- Knowledge base entries

## Usage

### Starting the Application

```bash
python app.py
```

The application will be available at: **http://localhost:5000**

### Default Accounts

**Manager:**
- Username: `manager`
- Password: `admin123`
- Access: Full system control via `/manager/dashboard`

**Chefs:**
- Username: `chef1` or `chef2`
- Password: `chef123`
- Access: Menu management via `/chef/dashboard`

**Delivery Personnel:**
- Username: `delivery1` or `delivery2`
- Password: `delivery123`
- Access: Delivery bidding via `/delivery/dashboard`

**Test Customer:**
- Username: `customer1`
- Password: `customer123`
- Access: Full customer features

### First-Time Setup

1. Visit `http://localhost:5000`
2. Browse the menu as a visitor
3. Test the AI chat feature (should work if Gemini/Ollama is configured)
4. Register a new account or login with test credentials
5. New registrations require manager approval

## Configuration

### Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# AI Provider Selection
LLM_PROVIDER=gemini          # or 'ollama'

# Gemini Configuration
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Ollama Configuration (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False
```

### Provider Selection Logic

The system automatically selects the provider:
1. If `GEMINI_API_KEY` is set → Uses Gemini (default)
2. If `LLM_PROVIDER=ollama` → Uses Ollama
3. Falls back to Ollama if Gemini API key is missing

## System Rules

### Customer Progression
- **New → Registered**: Manager approval required
- **Registered → VIP**: 
  - Spend $100+ total, OR
  - Make 3 orders without complaints
- **VIP Benefits**: 
  - 5% discount on all orders
  - 1 free delivery per 3 orders
  - Access to VIP-only dishes
- **Warnings**: 
  - Regular customers: 3 warnings = deregistration
  - VIP customers: 2 warnings = downgrade to regular
  - Deregistered users are blacklisted permanently

### Employee Performance
- **Chefs & Delivery Personnel:**
  - Low ratings (<2.0) or 3 complaints = demotion (salary cut)
  - 2 demotions = fired
  - High ratings (>4.0) or 3 compliments = bonus
- **Compliments**: Cancel out complaints (1:1 ratio)
- **VIP Compliments**: Count as 2x for employee bonuses

### Financial Rules
- All orders require sufficient deposit balance
- Insufficient funds = order rejected + 1 warning
- Kicked-out customers receive full deposit refund

### Reputation System
- Customers can rate food (1-5 stars) and delivery (1-5 stars) separately
- File complaints/compliments on chefs, delivery personnel, or other customers
- Disputed complaints reviewed by manager
- False complaints = 1 warning to complainant


## Key Web Pages

- `/` - Home page with featured dishes and recommendations
- `/menu` - Browse all dishes with filters and search
- `/login` - User login
- `/register` - New customer registration
- `/profile` - Customer profile and order history
- `/cart` - Shopping cart
- `/orders` - Order history with rating interface
- `/forum` - Discussion forums
- `/chat` - AI customer service chat
- `/meal-planner` - AI meal plan generator
- `/manager/dashboard` - Manager control panel
- `/chef/dashboard` - Chef menu management
- `/delivery/dashboard` - Delivery bidding interface

## 🔌 API Endpoints

### Chat & AI
- `POST /api/v1/chat` - Send message to AI customer service
- `GET /api/v1/recommendations` - Get personalized dish recommendations
- `POST /api/v1/meal-plan/generate` - Generate AI meal plan
- `GET /api/v1/nutrition/<dish_id>` - Get nutritional information

### Orders & Menu
- `GET /api/v1/menu` - Get dishes with filters (search, category, price, etc.)
- `POST /api/v1/order` - Place an order
- `POST /api/v1/rating` - Submit food/delivery rating
- `GET /api/v1/favorites` - Get user's favorite dishes

### User Management
- `POST /api/v1/complaint` - File complaint/compliment
- `POST /api/v1/knowledge/rate` - Rate knowledge base response

## Development

### Running in Development Mode

```bash
# Enable debug mode
export DEBUG=True  # Linux/Mac
set DEBUG=True     # Windows CMD

# Run with auto-reload
python app.py
```

### Reset Database

```bash
# WARNING: This deletes all data and reinitializes
python app.py --reset
```

### Adding New Dishes

1. Login as manager or chef
2. Navigate to chef dashboard (`/chef/dashboard`)
3. Click "Add New Dish"
4. Upload image, set price, add description and flavor tags
5. Dish appears on menu immediately

## Deployment

### Local Network Access

The application is configured to accept connections from other devices on your network:

```python
# Already set in config.py
FlaskConfig.HOST = "0.0.0.0"
```

Access from other devices: `http://<your-ip-address>:5000`

### Production Deployment

**Using Gunicorn (Linux/Mac):**
```bash
pip install gunicorn
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

**Important for Production:**
- Set a strong `SECRET_KEY` in environment variables
- Set `DEBUG=False`
- Use a production WSGI server (Gunicorn/Waitress)
- Configure proper firewall rules
- Use HTTPS with a reverse proxy (nginx/Apache)

## Troubleshooting

### AI Not Responding

**Gemini Issues:**
- Verify API key is set: `echo $GEMINI_API_KEY` (Linux/Mac) or `echo %GEMINI_API_KEY%` (Windows)
- Check API key is valid at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Verify internet connection (Gemini requires internet)
- Check for API quota limits
- Review error messages in terminal/console

**Ollama Issues:**
- Verify Ollama is running: `ollama list` (should show installed models)
- Check Ollama service: `curl http://localhost:11434/api/tags` (Linux/Mac)
- Ensure model is downloaded: `ollama pull llama3`
- Check firewall isn't blocking port 11434
- Verify model name matches: `echo $OLLAMA_MODEL` (should match installed model)

**General:**
- Check terminal/console for error messages
- Verify `LLM_PROVIDER` environment variable matches your setup
- Try switching providers to isolate the issue
- Check network connectivity

### Port Already in Use

```bash
# Change port in config.py or set environment variable
export PORT=5001  # Linux/Mac
set PORT=5001     # Windows CMD
```

### Static Files Not Loading

- Verify `static/` folder exists
- Check file paths in templates use `url_for('static', filename='...')`
- Clear browser cache
- Check file permissions

### Session Issues

```bash
# Clear Flask session files
rm -rf flask_session/  # Linux/Mac
rmdir /s flask_session  # Windows CMD
```

### Database Issues

```bash
# Reinitialize database (WARNING: deletes all data)
python app.py --reset
```

## Technologies Used

- **Flask 3.0**: Web framework
- **Jinja2**: Template engine
- **Bootstrap 5**: CSS framework
- **JavaScript/jQuery**: Frontend interactivity
- **Google Gemini API**: Cloud LLM integration
- **Ollama**: Local LLM integration
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

Atif Tausif
Mahdi Mahin
Mir Haque
Raian Pial
Arnob Hossain

## Acknowledgments

- **LLM Providers**: Google Gemini, Ollama
- **Course**: Software Engineering
- **Instructor**: Prof. Jie Wei



