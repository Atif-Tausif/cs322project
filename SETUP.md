# Quick Setup Guide

## Installation Steps

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database:**
   ```bash
   python app.py --init
   ```
   This will create default accounts:
   - Manager: `manager` / `admin123`
   - Chefs: `chef1`, `chef2` / `chef123`
   - Delivery: `delivery1`, `delivery2` / `delivery123`
   - Test Customer: `customer1` / `customer123`

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   - Open browser to: http://localhost:5000

## LLM Setup (Optional)

The AI chat feature requires either Ollama or HuggingFace:

### Option 1: Ollama (Recommended)
```bash
# Install Ollama from https://ollama.ai
ollama pull llama2
```

### Option 2: HuggingFace
- Get a free API token from https://huggingface.co
- Set environment variable: `HUGGINGFACE_TOKEN=your_token_here`
- Or edit `config.py` directly

## First Steps

1. Visit the homepage as a visitor
2. Register a new account (requires manager approval)
3. Login as manager to approve registrations
4. Login as customer to browse menu and place orders
5. Login as chef to add dishes
6. Login as delivery to bid on deliveries

## Project Structure

- `app.py` - Flask application entry point
- `routes.py` - All URL routes and endpoints
- `models.py` - Data models
- `database.py` - JSON storage operations
- `auth.py` - Authentication
- `services.py` - Business logic
- `ai_service.py` - LLM integration
- `config.py` - Configuration
- `utils.py` - Helper functions
- `templates/` - HTML templates
- `static/` - CSS, JS, images
- `data/` - JSON data files (created on first run)

## Troubleshooting

- **Port already in use**: Change `PORT` in `config.py`
- **LLM not working**: Check Ollama is running or HuggingFace token is set
- **Database issues**: Run `python app.py --reset` to reset
