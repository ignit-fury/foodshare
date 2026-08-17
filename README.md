# 🍏 FoodShare

Connecting surplus food with those who need it most. FoodShare is a waste food redistribution platform that connects food donors with receivers/NGOs to reduce food waste and fight hunger.

## 🚀 Key Features

- **Multi-Role Support**: Specialized portals for Donors, Receivers (NGOs), and Administrators.
- **Secure Verification**: Secure OTP (One-Time Password) system for donation pickup and delivery.
- **Real-time Notifications**: Instant alerts for new donations and status updates.
- **Admin Oversight**: Comprehensive admin dashboard for user verification (NGO proofs), donation monitoring, and error logging.
- **Dual Pickup/Delivery**: Support for both self-pickup and platform-managed delivery.
- **Donor Recognition**: Features "Star Donor" recognition to encourage community participation.

## 🛠️ Technology Stack

- **Backend**: Python with Flask
- **Database**: SQLite (via Flask-SQLAlchemy)
- **Authentication**: Flask-Login
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Styling**: Custom modern CSS with Glassmorphism elements

## 📦 Installation


1. **Clone the repository**:
   ```bash
   git clone https://github.com/ignit-fury/foodshare.git
   cd foodshare
   ```

2. **Set up a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   The application will automatically create the database on first run.

5. **Run the application**:
   ```bash
   python app.py
   ```

## 📁 Project Structure

- `app.py`: Main Flask application containing routes and business logic.
- `config.py`: Configuration settings.
- `db_utils.py`: Database utility functions.
- `templates/`: HTML templates for different views.
- `static/`: Static assets including CSS, JavaScript, and uploaded IDs/documents.
- `instance/`: SQLite database file.

## 🛡️ License

This project is for educational/community purposes.

---
Built with ❤️ to reduce food waste.

## ADMIN LOGIN CRED
Admin Id  = admin@foodshare.com
Admin Password = admin123
