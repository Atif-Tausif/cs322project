# Feature Map - Restaurant Order System

This document maps all system requirements to their implementation locations in the codebase.

## 1. User Groups

### 1.1 Employees

#### Chefs (at least 2)
- **Location**: `app.py` (lines 43-58) - Initialization creates chef1 and chef2
- **Menu Creation**: 
  - `routes.py` (lines 821-867) - `/chef/dish/add` endpoint
  - `templates/chef/add_dish.html` - UI for adding dishes
  - `templates/chef/dashboard.html` - Chef dashboard showing their dishes and orders
- **Independent Menu Decisions**: Chefs can create their own dishes via the dashboard
- **Dish Making**: Chefs update order status from "pending" to "preparing" to "ready"
  - `routes.py` (lines 914-966) - `/api/v1/order/update-status` endpoint

#### Delivery People (at least 2)
- **Location**: `app.py` (lines 60-74) - Initialization creates delivery1 and delivery2
- **Bidding System**: 
  - `routes.py` (lines 897-912) - `/api/v1/delivery/bid` endpoint
  - `templates/delivery/dashboard.html` - Shows available orders and bidding interface
- **Delivery Assignment**: Manager assigns based on bids
  - `routes.py` (lines 761-778) - `/manager/delivery/accept` endpoint
  - `services.py` (lines 364-439) - `accept_delivery_bid()` function

#### Manager (1)
- **Location**: `app.py` (lines 31-41) - Initialization creates manager account
- **Customer Registration Processing**: 
  - `routes.py` (lines 678-699) - `/manager/approve/<user_id>` and `/manager/reject/<user_id>`
  - `templates/manager/dashboard.html` (lines 36-82) - Pending user approvals section
- **Complaints/Compliments Handling**: 
  - `routes.py` (lines 701-715) - `/manager/complaint/resolve/<complaint_id>`
  - `services.py` (lines 273-299) - `resolve_complaint()` function
  - `templates/manager/dashboard.html` (lines 143-189) - Pending complaints section
- **Hire/Fire/Raise/Cut Pay**: 
  - `routes.py` (lines 780-850) - `/manager/hr/update` endpoint
  - `templates/manager/dashboard.html` (lines 357-422) - HR Management section
  - Automatic performance-based changes: `services.py` (lines 223-249) - `check_employee_performance()`
- **Knowledge Base Management**: 
  - `routes.py` (lines 717-759) - Knowledge base approval/removal
  - `templates/manager/dashboard.html` (lines 278-356) - Knowledge base sections

### 1.2 Customers

#### Registered Customers
- **Registration**: 
  - `routes.py` (lines 88-126) - `/register` endpoint
  - `templates/register.html` - Registration form
- **Browse/Search**: 
  - `routes.py` (lines 46-50) - `/menu` endpoint
  - `routes.py` (lines 302-382) - `/api/v1/menu` API with search/filter
  - `templates/menu.html` - Menu browsing interface
- **Order**: 
  - `routes.py` (lines 384-413) - `/api/v1/order` endpoint
  - `services.py` (lines 19-107) - `process_order()` function
  - `templates/cart.html` - Shopping cart
- **Vote (1-5 stars)**: 
  - Food rating: `routes.py` (lines 415-437) - `/api/v1/rating` endpoint
  - Delivery rating: Same endpoint, separate fields
  - `services.py` (lines 109-174) - `submit_rating()` function
  - `templates/orders.html` - Rating interface for delivered orders
- **Discussion Forums**: 
  - `routes.py` (lines 229-240) - `/forum` endpoint
  - `routes.py` (lines 614-650) - `/api/v1/forum/post` and `/api/v1/forum/reply` endpoints
  - `templates/forum.html` - Forum interface with posting and replying

#### VIP Customers
- **VIP Promotion**: 
  - `services.py` (lines 88-95) - Automatic promotion logic
  - Conditions: $100 spent OR 3 orders without complaints
- **5% Discount**: 
  - `services.py` (lines 40-41) - Discount calculation
  - `utils.py` (lines 57-61) - `calculate_discount()` function
  - Applied in cart: `templates/cart.html` (lines 223-226)
- **1 Free Delivery per 3 Orders**: 
  - `services.py` (lines 59-72) - Free delivery earning logic
  - `services.py` (lines 404-412) - Free delivery application
- **Special Dishes Access**: 
  - `models.py` (line 103) - `vip_only` flag on Dish model
  - `routes.py` (lines 339-341) - VIP filter in menu API
  - `routes.py` (lines 501-503) - VIP check when adding to cart
- **Complaints/Compliments Count Twice**: 
  - `services.py` (lines 206-207) - Weight calculation (VIP = 2x)
- **2 Warnings = Downgrade**: 
  - `services.py` (lines 301-338) - `check_customer_warnings()` function
  - `config.py` (line 50) - `MAX_WARNINGS_FOR_VIP_DOWNGRADE = 2`

### 1.3 Visitors
- **Browse Menus**: 
  - `routes.py` (lines 29-44) - `/` homepage shows popular/top-rated dishes
  - `routes.py` (lines 46-50) - `/menu` accessible without login
- **Ask Questions**: 
  - `routes.py` (lines 246-257) - `/api/v1/chat` endpoint
  - `ai_service.py` (lines 97-145) - `get_ai_response()` function
  - Chat widget available on all pages
- **Apply for Registration**: 
  - `routes.py` (lines 88-126) - `/register` endpoint
  - Registration requires manager approval

## 2. System Features

### 2.1 GUI with Pictures
- **Dish Images**: 
  - `models.py` (line 97) - `image` field on Dish model
  - `templates/menu.html` - Displays dish images
  - `templates/dish_detail.html` - Dish detail page with image
  - `utils.py` (lines 27-55) - `save_uploaded_image()` function
- **Chef Pictures**: 
  - `services.py` (lines 455-474) - `get_featured_chefs()` function
  - `templates/index.html` - Shows featured chefs with images
- **Personalized Recommendations**: 
  - `routes.py` (lines 259-271) - `/api/v1/recommendations` endpoint
  - `ai_service.py` (lines 147-199) - `get_personalized_recommendations()` function
  - Based on order history and flavor profile
- **Most Ordered Items**: 
  - `routes.py` (lines 273-300) - `/api/v1/favorites` endpoint
  - `services.py` (lines 441-446) - `get_popular_dishes()` function
- **Highest Rated Items**: 
  - `services.py` (lines 448-453) - `get_top_rated_dishes()` function
  - `routes.py` (lines 29-44) - Homepage displays top-rated dishes
- **Chat Box**: 
  - `routes.py` (lines 246-257) - `/api/v1/chat` endpoint
  - `ai_service.py` - AI service with knowledge base
  - Chat widget in `templates/base.html`

### 2.2 Reputation Management
- **File Complaints/Compliments**: 
  - `routes.py` (lines 439-462) - `/api/v1/complaint` endpoint
  - `services.py` (lines 176-221) - `file_complaint()` function
  - Can file against chefs, delivery people, or customers
- **Dispute Complaints**: 
  - `routes.py` (lines 464-478) - `/api/v1/complaint/dispute` endpoint
  - `services.py` (lines 251-271) - `dispute_complaint()` function
- **Manager Resolution**: 
  - `routes.py` (lines 701-715) - `/manager/complaint/resolve/<complaint_id>`
  - `services.py` (lines 273-299) - `resolve_complaint()` function
  - Can uphold or dismiss complaints
- **False Complaint Warning**: 
  - `services.py` (lines 287-292) - Warns complainant if complaint dismissed
- **Warning Display**: 
  - `templates/base.html` (lines 104-126) - Warning banner at top of page
  - `templates/profile.html` (lines 40-42) - Warnings shown in profile
- **3 Warnings = Deregistration**: 
  - `services.py` (lines 308-318) - Deregistration logic
  - `config.py` (line 49) - `MAX_WARNINGS_BEFORE_DEREGISTRATION = 3`
- **VIP 2 Warnings = Downgrade**: 
  - `services.py` (lines 305-313) - VIP downgrade logic
  - `config.py` (line 50) - `MAX_WARNINGS_FOR_VIP_DOWNGRADE = 2`
- **Compliment Cancels Complaint (1:1)**: 
  - `services.py` (lines 215-217) - Compliment cancellation logic

### 2.3 Finance Management
- **Deposit System**: 
  - `models.py` (line 17) - `balance` field on User model
  - `routes.py` (lines 972-1011) - Balance management (dev/testing)
  - `templates/dev/balance.html` - Balance management interface
- **Insufficient Balance = Warning**: 
  - `services.py` (lines 44-57) - Balance check and warning addition
- **Order Rejection**: 
  - `services.py` (lines 44-57) - Order rejected if insufficient balance
- **Account Closure Refund**: 
  - `routes.py` (lines 852-881) - `/manager/account/close` endpoint
  - Refunds balance when account is closed

### 2.4 Human Resources
- **Account Closure**: 
  - `routes.py` (lines 852-881) - `/manager/account/close` endpoint
  - Clears deposit and closes account
  - Option to blacklist user
- **Blacklist**: 
  - `models.py` (line 24) - `blacklisted` flag on User model
  - `routes.py` (lines 106-111) - Check blacklist during registration
- **Chef Performance Tracking**: 
  - Low ratings (<2) or 3 complaints = demotion
    - `services.py` (lines 228-234) - Demotion logic
    - `config.py` (lines 53, 55) - Thresholds
  - 2 demotions = fired
    - `services.py` (lines 236-239) - Firing logic
    - `config.py` (line 57) - `DEMOTIONS_BEFORE_FIRING = 2`
  - High ratings (>4) or 3 compliments = bonus
    - `services.py` (lines 241-247) - Bonus logic
    - `config.py` (lines 54, 56) - Thresholds
- **Delivery People Performance**: Same rules as chefs (same function)
- **Compliment Cancels Complaint**: 
  - `services.py` (lines 215-217) - 1:1 cancellation ratio
- **Manager HR Interface**: 
  - `routes.py` (lines 780-850) - `/manager/hr/update` endpoint
  - `templates/manager/dashboard.html` (lines 357-422) - HR Management UI
  - Can manually hire, fire, raise, cut, or set salary
- **Delivery Bidding**: 
  - `routes.py` (lines 897-912) - `/api/v1/delivery/bid` endpoint
  - `services.py` (lines 340-362) - `submit_delivery_bid()` function
  - Manager assigns based on lowest bid
  - `routes.py` (lines 761-778) - `/manager/delivery/accept` endpoint
  - `services.py` (lines 364-439) - `accept_delivery_bid()` function
  - Memo required if choosing higher bid
    - `services.py` (lines 383-387) - Memo validation

## 3. File Structure

### Core Application Files
- **`app.py`**: Application entry point, database initialization
- **`routes.py`**: All Flask routes and endpoints (1012 lines)
- **`services.py`**: Business logic services (475 lines)
- **`models.py`**: Data models (User, Dish, Order, Rating, Complaint, ForumPost, DeliveryBid)
- **`database.py`**: JSON-based database operations
- **`auth.py`**: Authentication and session management
- **`config.py`**: Configuration settings and knowledge base
- **`utils.py`**: Utility functions (password hashing, image upload, discounts)
- **`ai_service.py`**: AI chat and recommendation services

### Template Files
- **`templates/base.html`**: Base template with navigation and warning banner
- **`templates/index.html`**: Homepage with popular/top-rated dishes
- **`templates/menu.html`**: Menu browsing with filters
- **`templates/dish_detail.html`**: Individual dish page
- **`templates/cart.html`**: Shopping cart
- **`templates/orders.html`**: Order history with rating interface
- **`templates/profile.html`**: User profile with warnings and complaints
- **`templates/forum.html`**: Discussion forum with posting and replies
- **`templates/login.html`**: Login page
- **`templates/register.html`**: Registration page
- **`templates/chef/dashboard.html`**: Chef dashboard
- **`templates/chef/add_dish.html`**: Add dish form
- **`templates/delivery/dashboard.html`**: Delivery dashboard
- **`templates/manager/dashboard.html`**: Manager dashboard with all management features
- **`templates/dev/balance.html`**: Balance management (testing)

## 4. Key Features by File

### `services.py`
- Order processing with balance checks and warnings
- Rating submission and updates
- Complaint/compliment filing with VIP weighting
- Compliment canceling complaints (1:1 ratio)
- Employee performance checking (automatic demotion/promotion)
- Customer warning checking (downgrade/deregistration)
- Delivery bid submission and acceptance
- Popular/top-rated dishes retrieval
- Featured chefs retrieval

### `routes.py`
- All HTTP endpoints
- Authentication routes (login, register, logout)
- Customer routes (profile, orders, cart, forum)
- Chef routes (dashboard, add dish, update order status)
- Delivery routes (dashboard, bid submission)
- Manager routes (dashboard, approvals, complaints, HR, delivery assignment, knowledge base)
- API endpoints (menu, order, rating, complaint, forum, chat, recommendations)

### `models.py`
- User model with all role-specific fields
- Dish model with ratings, orders, VIP flag
- Order model with status tracking, ratings, delivery info
- Rating model for dishes and delivery
- Complaint model with dispute resolution
- ForumPost model with replies
- DeliveryBid model with manager memo

### `database.py`
- JSON file-based storage
- CRUD operations for all models
- Knowledge base management
- Knowledge rating system

### `ai_service.py`
- Knowledge base search
- LLM integration (Ollama/HuggingFace)
- Personalized recommendations
- Flavor profile analysis

## 5. Configuration

### `config.py`
- VIP thresholds ($100 or 3 orders)
- VIP benefits (5% discount, free delivery ratio)
- Warning limits (3 for customers, 2 for VIP)
- Employee performance thresholds (ratings, complaints, compliments)
- File upload settings
- Knowledge base entries

## 6. Missing Features (Now Implemented)

All requirements have been implemented:
- ✅ Forum posting API (`/api/v1/forum/post`)
- ✅ Forum reply API (`/api/v1/forum/reply`)
- ✅ Manager HR management (`/manager/hr/update`)
- ✅ Compliment canceling complaint (1:1 ratio)
- ✅ Account closure with refund (`/manager/account/close`)

## 7. Testing Checklist

To verify all features work:
1. Register as customer → Manager approves
2. Make orders → Become VIP (spend $100 or 3 orders)
3. Rate food and delivery (1-5 stars)
4. File complaints/compliments
5. Dispute complaints
6. Manager resolves complaints
7. Test warning system (insufficient balance, false complaints)
8. Test VIP downgrade (2 warnings)
9. Test deregistration (3 warnings)
10. Chef creates dishes
11. Delivery people bid on orders
12. Manager assigns delivery (lowest bid, or higher with memo)
13. Manager manages HR (hire/fire/raise/cut)
14. Post and reply in forum
15. Use chat with knowledge base
16. Test blacklist (kicked-out users can't register)

