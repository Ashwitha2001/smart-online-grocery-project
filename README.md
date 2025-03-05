# Smart Grocery Online Delivery System

## Overview
Smart Grocery is an online grocery delivery system built using Django. It allows users to browse groceries, place orders, and track deliveries. The platform supports multiple user roles, including customers, vendors, delivery personnel, and admins.

## Features
- **User Authentication & Role-Based Access**
  - Customers, vendors, delivery personnel, and admin roles.
  - Secure login, registration, and role-specific dashboards.

- **Product Management**
  - Vendors can add, edit, and delete grocery items.
  - Customers can browse products and add them to the cart.

- **Order Management**
  - Customers can place orders and track their status.
  - Vendors can manage inventory and process orders.

- **Delivery Management (Real-Time Updates)**
  - Delivery personnel can update order statuses.
  - Real-time tracking using WebSockets (Django Channels).

- **Payment Integration (Razorpay)**
  - Online payments processed securely using **Razorpay**.
  - Customers can pay via UPI, debit/credit cards, and net banking.

- **Admin Dashboard**
  - Manage users, orders, and system configurations.

## Tech Stack
- **Backend:** Django (Python)
- **Frontend:** HTML, CSS
- **Database:** SQLite (for development)
- **Real-Time Updates:** WebSockets (Django Channels, Daphne, Redis)
- **Payment Gateway:** Razorpay
- **Authentication:** Django's built-in auth system

## Installation
### Prerequisites
- Python (3.8 or later)
- Django (4.2)
- SQLite
- **Redis** (for real-time WebSocket communication)
- **Daphne** (for ASGI server)
- Razorpay API keys (for payment processing)

### Steps to Run the Project
1. **Clone the Repository**
   ```sh
   git clone https://github.com/Ashwitha2001/smart-online-grocery-project.git
   cd smart-online-grocery-project
   ```

2. **Create and Activate a Virtual Environment**
   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```sh
   pip install -r requirements.txt
   ```

4. **Install and Start Redis** (Required for WebSockets)
     ```sh
     docker run --name redis -p 6379:6379 -d redis
     ```

5. **Set Up Environment Variables**
   Create a `.env` file in the project root and add:
   ```env
   RAZORPAY_KEY_ID=your_key_id
   RAZORPAY_KEY_SECRET=your_secret_key
   ```

6. **Run Migrations**
   ```sh
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create a Superuser (Admin)**
   ```sh
   python manage.py createsuperuser
   ```

8. **Run the Daphne ASGI Server (For Real-Time Tracking)**
   ```sh
   daphne -b 0.0.0.0 -p 8001 smart_grocery.asgi:application
   ```

9. **Run the Django Development Server (In a Separate Terminal)**
   ```sh
   python manage.py runserver
   ```

10. **Access the Application**
   - Open `http://127.0.0.1:8000/` in your browser.
   - Admin Panel: `http://127.0.0.1:8000/admin/`

## Folder Structure
```
smart_grocery/
│── grocery/               # Main app
│   ├── migrations/        # Database migrations
│   ├── static/            # Static files (CSS, JS, images)
│   ├── templates/         # HTML templates
│   ├── views.py           # Application logic
│   ├── models.py          # Database models
│   ├── urls.py            # URL routing
│── smart_grocery/         # Project settings
│── asgi.py                # ASGI config for WebSockets
│── manage.py              # Django management script
│── requirements.txt       # Dependencies
│── README.md              # Project documentation
│── .env                   # Environment variables (Razorpay API keys)
```
