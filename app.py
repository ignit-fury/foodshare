from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from config import Config
import random
import os
import traceback
import json
import csv
import io
from flask import make_response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'ids'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'docs'), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    role = db.Column(db.String(20), nullable=False)
    org_name = db.Column(db.String(100))
    org_id_proof = db.Column(db.String(200))
    personal_id_proof = db.Column(db.String(200), nullable=False)
    aadhar_number = db.Column(db.String(14))
    status = db.Column(db.String(20), default='approved')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    donations = db.relationship('Donation', backref='donor', lazy=True, foreign_keys='Donation.donor_id')
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(200), nullable=False)
    food_type = db.Column(db.String(20), nullable=False)
    food_category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(20), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.Text, nullable=False)
    pickup_location = db.Column(db.String(200))
    phone = db.Column(db.String(20), nullable=False)
    pickup_time = db.Column(db.String(100))
    instructions = db.Column(db.Text)
    status = db.Column(db.String(20), default='available')
    otp = db.Column(db.String(4))
    donor_otp = db.Column(db.String(4))
    claimed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    claimed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    delivery_method = db.Column(db.String(20), default='self_pickup')
    delivery_address = db.Column(db.Text)
    delivery_status = db.Column(db.String(20))
    delivery_notes = db.Column(db.Text)
    
    donation_type = db.Column(db.String(20), default='immediate')
    scheduled_date = db.Column(db.Date)
    pickup_window_start = db.Column(db.String(10))
    pickup_window_end = db.Column(db.String(10))
    storage_method = db.Column(db.String(30))
    preparation_time = db.Column(db.DateTime)
    storage_instructions = db.Column(db.Text)
    intended_meal = db.Column(db.String(20))
    
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime)
    picked_up_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    claimer = db.relationship('User', foreign_keys=[claimed_by], backref='claims')
    delivery_partner = db.relationship('User', foreign_keys=[assigned_to], backref='deliveries')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DonorRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('donation.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    donation = db.relationship('Donation', backref='ratings')
    donor = db.relationship('User', foreign_keys=[donor_id], backref='received_ratings')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='given_ratings')
    
    __table_args__ = (db.UniqueConstraint('donation_id', 'receiver_id', name='_donation_receiver_uc'),)

class ErrorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    traceback = db.Column(db.Text)
    endpoint = db.Column(db.String(200))
    method = db.Column(db.String(10))
    severity = db.Column(db.String(20), default='error')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='errors_triggered')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='errors_resolved')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_otp():
    return str(random.randint(1000, 9999))

def add_notification(user_id, message):
    notif = Notification(user_id=user_id, message=message)
    db.session.add(notif)
    db.session.commit()

def log_error(error, severity='error', notes=None):
    """Log an error to the database with full context"""
    try:
        error_type = type(error).__name__
        error_message = str(error)
        tb = traceback.format_exc() if traceback.format_exc() != 'NoneType: None\n' else None
        
        endpoint = None
        method = None
        ip_address = None
        user_agent = None
        user_id = None
        
        try:
            from flask import request
            if request:
                endpoint = request.endpoint or request.path
                method = request.method
                ip_address = request.remote_addr
                user_agent = str(request.user_agent)[:300] if request.user_agent else None
        except RuntimeError:
            pass
        
        try:
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
        except:
            pass
        
        error_log = ErrorLog(
            error_type=error_type,
            error_message=error_message[:1000],
            traceback=tb,
            endpoint=endpoint,
            method=method,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes
        )
        
        db.session.add(error_log)
        db.session.commit()
        return error_log.id
    except Exception as e:
        print(f"Failed to log error: {e}")
        db.session.rollback()
        return None

@app.errorhandler(404)
def not_found_error(error):
    log_error(error, severity='warning', notes='Page not found')
    return render_template('error.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    log_error(error, severity='critical', notes='Internal server error')
    return render_template('error.html', error_code=500, error_message='Internal server error'), 500

@app.errorhandler(Exception)
def unhandled_exception(error):
    db.session.rollback()
    log_error(error, severity='critical', notes='Unhandled exception')
    return render_template('error.html', error_code=500, error_message='Something went wrong'), 500

@app.route('/')
def index():
    top_donor_data = None
    
    donors = User.query.filter_by(role='donor').all()
    if donors:
        sorted_donors = sorted(donors, key=lambda u: len(u.donations), reverse=True)
        if sorted_donors and len(sorted_donors[0].donations) > 0:
            top_user = sorted_donors[0]
            count = len(top_user.donations)
            
            if count >= 5:
                
                types = [d.food_type for d in top_user.donations]
                specialty =  max(set(types), key=types.count)
                specialty_label = {
                    'veg': 'Vegetarian Delights 🥬',
                    'nonveg': 'Non-Veg Feasts g🍗',
                    'vegan': 'Vegan Specialties 🌱'
                }.get(specialty, 'Mixed Variety 🥘')
                
                top_donor_data = {
                    'name': top_user.name,
                    'org': top_user.org_name,
                    'count': count,
                    'specialty': specialty_label,
                    'member_since': top_user.created_at.strftime('%b %Y')
                }

    return render_template('index.html', top_donor=top_donor_data)

@app.route('/auth')
def auth():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}_dashboard'))
    return render_template('auth.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    
    if User.query.filter_by(email=data['email']).first():
        flash('Email already registered!', 'error')
        return redirect(url_for('auth'))
        
    personal_file = request.files.get('personalId')
    org_file = request.files.get('orgProof')
    
    if not personal_file or personal_file.filename == '':
        flash('Personal ID Proof is required!', 'error')
        return redirect(url_for('auth'))
        
    if data['role'] == 'receiver' and (not org_file or org_file.filename == ''):
        flash('Organization Proof is required for Receivers!', 'error')
        return redirect(url_for('auth'))

    if personal_file and allowed_file(personal_file.filename):
        filename = secure_filename(f"pid_{data['phone']}_{personal_file.filename}")
        personal_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ids', filename)
        personal_file.save(personal_path)
        db_personal_path = f"uploads/ids/{filename}"
    else:
        flash('Invalid Personal ID file type!', 'error')
        return redirect(url_for('auth'))

    db_org_path = None
    if data['role'] == 'receiver':
        if org_file and allowed_file(org_file.filename):
            filename = secure_filename(f"org_{data['phone']}_{org_file.filename}")
            org_path = os.path.join(app.config['UPLOAD_FOLDER'], 'docs', filename)
            org_file.save(org_path)
            db_org_path = f"uploads/docs/{filename}"
        else:
            flash('Invalid Organization Proof file type!', 'error')
            return redirect(url_for('auth'))
    
    user = User(
        name=data['name'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        phone=data['phone'],
        address=data['address'],
        role=data['role'],
        org_name=data.get('orgName'),
        org_id_proof=db_org_path,
        personal_id_proof=db_personal_path,
        aadhar_number=data.get('aadhar'),
        status='pending' if data['role'] == 'receiver' else 'approved'
    )
    
    db.session.add(user)
    db.session.commit()
    
    if data['role'] == 'receiver':
        flash('Registration successful! Please wait for admin approval.', 'success')
    else:
        flash('Registration successful! You can now login.', 'success')
    
    return redirect(url_for('auth'))

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    email = data['email']
    password = data['password']
    role = data['role']
    
    if role == 'admin':
        if email == 'admin@foodshare.com' and password == 'admin123':
            admin = User.query.filter_by(email=email, role='admin').first()
            if not admin:
                admin = User(
                    name='Administrator',
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='admin',
                    status='approved',
                    personal_id_proof='system'
                )
                db.session.add(admin)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    admin = User.query.filter_by(email=email, role='admin').first()
                    if not admin:
                        flash('Error creating admin account!', 'error')
                        return redirect(url_for('auth'))
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials!', 'error')
        return redirect(url_for('auth'))
    
    user = User.query.filter_by(email=email, role=role).first()
    
    if user and check_password_hash(user.password_hash, password):
        if user.status == 'pending':
            flash('Your account is pending admin approval.', 'warning')
            return redirect(url_for('auth'))
        if user.status == 'rejected':
            flash('Your registration was rejected.', 'error')
            return redirect(url_for('auth'))
        if user.status == 'banned':
            flash('Your account has been suspended.', 'error')
            return redirect(url_for('auth'))
        
        login_user(user)
        return redirect(url_for(f'{user.role}_dashboard'))
    
    flash('Invalid email or password!', 'error')
    return redirect(url_for('auth'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/donor')
@login_required
def donor_dashboard():
    if current_user.role != 'donor':
        return redirect(url_for('index'))
    donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.created_at.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    
    ratings = DonorRating.query.filter_by(donor_id=current_user.id).order_by(DonorRating.created_at.desc()).all()
    average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else None
    total_ratings = len(ratings)
    
    return render_template('donor.html', 
        donations=donations, 
        notifications=notifications, 
        unread_count=unread_count,
        average_rating=average_rating,
        total_ratings=total_ratings,
        ratings=ratings
    )

@app.route('/donor/donate', methods=['POST'])
@login_required
def post_donation():
    if current_user.role != 'donor':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.form
    donation_type = data.get('donationType', 'immediate')
    
    donation = Donation(
        donor_id=current_user.id,
        food_name=data['foodName'],
        food_type=data['foodType'],
        food_category=data['foodCategory'],
        quantity=data['quantity'],
        urgency=data['urgency'],
        address=data['address'],
        pickup_location=data.get('pickupLocation'),
        phone=data['phone'],
        instructions=data.get('instructions'),
        donation_type=donation_type
    )
    
    if donation_type == 'scheduled':
        from datetime import date, time
        
        scheduled_date_str = data.get('scheduledDate')
        if scheduled_date_str:
            donation.scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
        else:
            donation.scheduled_date = (datetime.utcnow() + timedelta(days=1)).date()
        
        donation.pickup_window_start = data.get('pickupWindowStart', '09:00')
        donation.pickup_window_end = data.get('pickupWindowEnd', '11:00')
        
        donation.storage_method = data.get('storageMethod', 'refrigerated')
        donation.storage_instructions = data.get('storageInstructions', '')
        donation.intended_meal = data.get('intendedMeal', 'any')
        
        prep_time_str = data.get('preparationTime')
        if prep_time_str:
            prep_hour, prep_min = map(int, prep_time_str.split(':'))
            donation.preparation_time = datetime.utcnow().replace(hour=prep_hour, minute=prep_min, second=0)
        else:
            donation.preparation_time = datetime.utcnow()
        
        storage_multiplier = {'room_temp': 1.0, 'refrigerated': 4.0, 'frozen': 30.0}
        base_hours = {'cooked': 4, 'raw': 24, 'packaged': 168, 'fruits': 48, 'bakery': 72, 'beverages': 72}
        
        base = base_hours.get(data['foodCategory'], 24)
        multiplier = storage_multiplier.get(donation.storage_method, 1.0)
        safe_hours = int(base * multiplier)
        
        donation.expiry = donation.preparation_time + timedelta(hours=safe_hours)
        
        donation.urgency = 'low'
        
        receivers = User.query.filter_by(role='receiver', status='approved').all()
        pickup_date = donation.scheduled_date.strftime('%b %d')
        for receiver in receivers:
            add_notification(receiver.id, 
                f"🌙 Scheduled food available: {donation.food_name} ({donation.food_type}) - Pickup on {pickup_date} between {donation.pickup_window_start} - {donation.pickup_window_end}")
        
        flash('Scheduled donation posted successfully! Food will be available for pickup tomorrow.', 'success')
    else:
        donation.expiry = datetime.utcnow() + timedelta(hours=int(data['safeFor']))
        donation.pickup_time = data.get('pickupTime')
        
        receivers = User.query.filter_by(role='receiver', status='approved').all()
        for receiver in receivers:
            add_notification(receiver.id, 
                f"New food available: {donation.food_name} ({donation.food_type}) - {donation.quantity}")
        
        flash('Donation posted successfully!', 'success')
    
    db.session.add(donation)
    db.session.commit()
    
    return redirect(url_for('donor_dashboard'))

@app.route('/donor/verify', methods=['POST'])
@login_required
def verify_pickup():
    data = request.json
    donation = Donation.query.get(data['donationId'])
    
    if not donation:
        return jsonify({'success': False, 'message': 'Donation not found'})
        
    if (donation.otp == data['otp']) or (donation.donor_otp == data['otp']):
        donation.status = 'completed'
        donation.completed_at = datetime.utcnow()
        if donation.delivery_method == 'foodshare_delivery':
            donation.delivery_status = 'in_transit'
        
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid OTP'})

@app.route('/receiver')
@login_required
def receiver_dashboard():
    if current_user.role != 'receiver':
        return redirect(url_for('index'))
    if current_user.status != 'approved':
        flash('Your account is pending approval.', 'warning')
        return redirect(url_for('index'))
    
    available = Donation.query.filter_by(status='available').order_by(Donation.created_at.desc()).all()
    my_claims = Donation.query.filter_by(claimed_by=current_user.id).order_by(Donation.created_at.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    
    return render_template('receiver.html', available=available, my_claims=my_claims, 
                         notifications=notifications, unread_count=unread_count)

@app.route('/receiver/claim/<int:donation_id>', methods=['POST'])
@login_required
def claim_donation(donation_id):
    if current_user.role != 'receiver':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    donation = Donation.query.get(donation_id)
    
    if not donation or donation.status != 'available':
        return jsonify({'success': False, 'message': 'Food not available'}), 400
    
    data = request.get_json() or {}
    delivery_choice = data.get('delivery_choice', 'pickup')
    
    donation.status = 'claimed'
    donation.claimed_by = current_user.id
    donation.claimed_at = datetime.utcnow()
    
    if delivery_choice == 'delivery':
        donor_otp = generate_otp()
        receiver_otp = generate_otp()
        
        donation.donor_otp = donor_otp
        donation.otp = receiver_otp
        donation.delivery_method = 'foodshare_delivery'
        donation.delivery_address = current_user.address or current_user.org_name
        donation.delivery_status = 'pending'
        
        db.session.commit()
        
        add_notification(donation.donor_id,
            f"🚚 {current_user.org_name or current_user.name} requested delivery for '{donation.food_name}'. Your OTP: {donor_otp}")
        
        print(f"\n{'='*60}")
        print(f"� DELIVERY - DUAL OTP")
        print(f"Food: {donation.food_name}")
        print(f"Donor OTP: {donor_otp} | Receiver OTP: {receiver_otp}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'delivery_choice': 'delivery',
            'receiver_otp': receiver_otp,
            'delivery_address': donation.delivery_address,
            'donor_name': donation.donor.name
        })
    else:
        otp = generate_otp()
        donation.otp = otp
        donation.delivery_method = 'self_pickup'
        
        db.session.commit()
        
        add_notification(donation.donor_id, 
            f'Your donation "{donation.food_name}" has been claimed by {current_user.org_name or current_user.name}. OTP: {otp}')
        
        print(f"\n{'='*60}")
        print(f"📦 PICKUP - SINGLE OTP: {otp}")
        print(f"Food: {donation.food_name}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'delivery_choice': 'pickup',
            'otp': otp,
            'donor_name': donation.donor.name,
            'pickup_address': donation.address,
            'pickup_location': donation.pickup_location,
            'donor_phone': donation.phone
        })

@app.route('/delivery')
@login_required
def delivery_dashboard():
    if current_user.role != 'delivery':
        return redirect(url_for('index'))
    
    available = Donation.query.filter_by(
        delivery_method='foodshare_delivery',
        delivery_status='pending'
    ).filter(Donation.assigned_to == None).order_by(Donation.created_at.desc()).all()
    
    my_active = Donation.query.filter(
        Donation.assigned_to == current_user.id,
        Donation.delivery_status.in_(['assigned', 'picked_up', 'in_transit'])
    ).order_by(Donation.assigned_at.desc()).all()
    
    my_completed = Donation.query.filter(
        Donation.assigned_to == current_user.id,
        Donation.delivery_status == 'delivered'
    ).order_by(Donation.delivered_at.desc()).limit(10).all()
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    
    today_count = Donation.query.filter(
        Donation.assigned_to == current_user.id,
        Donation.delivery_status == 'delivered',
        db.func.date(Donation.delivered_at) == datetime.utcnow().date()
    ).count()
    
    total_completed = Donation.query.filter(
        Donation.assigned_to == current_user.id,
        Donation.delivery_status == 'delivered'
    ).count()
    
    return render_template('delivery.html',
        available=available,
        my_active=my_active,
        my_completed=my_completed,
        notifications=notifications,
        unread_count=unread_count,
        today_count=today_count,
        total_completed=total_completed
    )

@app.route('/delivery/accept/<int:donation_id>', methods=['POST'])
@login_required
def accept_delivery(donation_id):
    if current_user.role != 'delivery':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    donation = Donation.query.get(donation_id)
    if not donation or donation.delivery_status != 'pending' or donation.assigned_to:
        return jsonify({'success': False, 'message': 'Delivery not available'}), 400
    
    donation.assigned_to = current_user.id
    donation.assigned_at = datetime.utcnow()
    donation.delivery_status = 'assigned'
    
    db.session.commit()
    
    add_notification(donation.donor_id,
        f"🚴 Driver {current_user.name} will pick up your donation '{donation.food_name}'")
    
    if donation.claimed_by:
        add_notification(donation.claimed_by,
            f"🚴 Driver {current_user.name} is assigned to deliver '{donation.food_name}' to you")
    
    return jsonify({
        'success': True,
        'donor_name': donation.donor.name,
        'donor_phone': donation.phone,
        'donor_address': donation.address,
        'donor_otp': donation.donor_otp,
        'receiver_name': donation.claimer.org_name or donation.claimer.name if donation.claimer else '',
        'receiver_phone': donation.claimer.phone if donation.claimer else '',
        'delivery_address': donation.delivery_address
    })

@app.route('/delivery/pickup/<int:donation_id>', methods=['POST'])
@login_required
def verify_delivery_pickup(donation_id):
    if current_user.role != 'delivery':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json
    donation = Donation.query.get(donation_id)
    
    if not donation or donation.assigned_to != current_user.id:
        return jsonify({'success': False, 'message': 'Not your delivery'}), 400
    
    if donation.donor_otp != data.get('otp'):
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    donation.delivery_status = 'in_transit'
    donation.picked_up_at = datetime.utcnow()
    
    db.session.commit()
    
    if donation.claimed_by:
        add_notification(donation.claimed_by,
            f"📦 Your food '{donation.food_name}' has been picked up and is on the way!")
    
    return jsonify({
        'success': True,
        'receiver_otp': donation.otp,
        'delivery_address': donation.delivery_address,
        'receiver_name': donation.claimer.org_name or donation.claimer.name if donation.claimer else '',
        'receiver_phone': donation.claimer.phone if donation.claimer else ''
    })

@app.route('/delivery/complete/<int:donation_id>', methods=['POST'])
@login_required
def complete_delivery(donation_id):
    if current_user.role != 'delivery':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json
    donation = Donation.query.get(donation_id)
    
    if not donation or donation.assigned_to != current_user.id:
        return jsonify({'success': False, 'message': 'Not your delivery'}), 400
    
    if donation.otp != data.get('otp'):
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    donation.delivery_status = 'delivered'
    donation.delivered_at = datetime.utcnow()
    donation.status = 'completed'
    donation.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    add_notification(donation.donor_id,
        f"✅ Your donation '{donation.food_name}' was successfully delivered!")
    
    if donation.claimed_by:
        add_notification(donation.claimed_by,
            f"✅ Your food '{donation.food_name}' has been delivered!")
    
    return jsonify({'success': True})

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    users = User.query.filter(User.role != 'admin').order_by(User.created_at.desc()).all()
    pending_users = User.query.filter_by(status='pending').count()
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    all_ratings = DonorRating.query.order_by(DonorRating.created_at.desc()).all()
    
    error_logs = ErrorLog.query.order_by(ErrorLog.created_at.desc()).limit(100).all()
    today = datetime.utcnow().date()
    
    error_data = {}
    for e in error_logs:
        error_data[str(e.id)] = {
            'id': str(e.id),
            'error_type': e.error_type or '',
            'error_message': (e.error_message or '')[:500],
            'traceback': e.traceback or 'No traceback available',
            'endpoint': e.endpoint or 'N/A',
            'method': e.method or 'N/A',
            'severity': e.severity or 'error',
            'status': e.status or 'new',
            'ip_address': e.ip_address or 'N/A',
            'user_agent': (e.user_agent or 'N/A')[:100],
            'created_at': e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else 'N/A',
            'user': e.user.name if e.user else 'Anonymous',
            'notes': e.notes or ''
        }
    error_data_json = json.dumps(error_data)
    
    stats = {
        'total_users': User.query.filter(User.role != 'admin').count(),
        'total_donors': User.query.filter_by(role='donor').count(),
        'total_receivers': User.query.filter_by(role='receiver').count(),
        'pending_approvals': pending_users,
        'total_donations': Donation.query.count(),
        'available_donations': Donation.query.filter_by(status='available').count(),
        'completed_donations': Donation.query.filter_by(status='completed').count(),
        'total_errors': ErrorLog.query.count(),
        'errors_today': ErrorLog.query.filter(db.func.date(ErrorLog.created_at) == today).count(),
        'unresolved_errors': ErrorLog.query.filter(ErrorLog.status != 'resolved').count(),
        'critical_errors': ErrorLog.query.filter_by(severity='critical', status='new').count()
    }
    
    return render_template('admin.html', users=users, donations=donations, stats=stats, 
                          all_ratings=all_ratings, error_logs=error_logs, error_data_json=error_data_json)

@app.route('/admin/user/<int:user_id>/status', methods=['POST'])
@login_required
def update_user_status(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False}), 403
    
    data = request.json
    user = User.query.get(user_id)
    
    if user:
        user.status = data['status']
        db.session.commit()
        
        if data['status'] == 'approved':
            add_notification(user.id, 'Your account has been approved! You can now access the marketplace.')
        elif data['status'] == 'rejected':
            add_notification(user.id, 'Your registration was not approved. Please contact support.')
        
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/admin/user/<int:user_id>/delete', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False}), 403
    
    user = User.query.get(user_id)
    if user:
        Donation.query.filter_by(donor_id=user.id).delete()
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/admin/errors/<int:error_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_error(error_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    error = ErrorLog.query.get(error_id)
    if error:
        error.status = 'acknowledged'
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Error not found'}), 404

@app.route('/admin/errors/<int:error_id>/resolve', methods=['POST'])
@login_required
def resolve_error(error_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json or {}
    error = ErrorLog.query.get(error_id)
    if error:
        error.status = 'resolved'
        error.resolved_at = datetime.utcnow()
        error.resolved_by = current_user.id
        error.notes = data.get('notes', '')
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Error not found'}), 404

@app.route('/admin/errors/<int:error_id>/delete', methods=['DELETE'])
@login_required
def delete_error(error_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    error = ErrorLog.query.get(error_id)
    if error:
        db.session.delete(error)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Error not found'}), 404

@app.route('/api/errors')
@login_required
def get_errors():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    errors = ErrorLog.query.order_by(ErrorLog.created_at.desc()).limit(100).all()
    return jsonify([{
        'id': e.id,
        'error_type': e.error_type,
        'error_message': e.error_message[:200] if e.error_message else '',
        'severity': e.severity,
        'status': e.status,
        'endpoint': e.endpoint,
        'method': e.method,
        'created_at': e.created_at.isoformat() if e.created_at else None,
        'user': e.user.name if e.user else None
    } for e in errors])

@app.route('/admin/donations/export')
@login_required
def export_donations():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Food Name', 'Type', 'Category', 'Quantity', 'Donor', 'Status', 'OTP', 'Claimed By', 'Created At'])
    
    for d in donations:
        cw.writerow([
            d.id, 
            d.food_name, 
            d.food_type, 
            d.food_category, 
            d.quantity,
            d.donor.name,
            d.status,
            d.otp or '',
            d.claimer.name if d.claimer else '',
            d.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=donations.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/donations/delete_all', methods=['POST'])
@login_required
def delete_all_donations():
    if current_user.role != 'admin':
        return jsonify({'success': False}), 403
    
    try:
        # Delete dependent ratings first if needed, though they shouldn't exist if we clear donations usually
        # But let's just delete donations. Ratings have foreign key constraints?
        # Check DonorRating model: donation_id nullable=False.
        # So we must delete ratings first.
        DonorRating.query.delete()
        Donation.query.delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting donations: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/errors/export')
@login_required
def export_errors():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    errors = ErrorLog.query.order_by(ErrorLog.created_at.desc()).all()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Severity', 'Type', 'Message', 'Endpoint', 'Method', 'Status', 'User', 'Time', 'Traceback'])
    
    for e in errors:
        cw.writerow([
            e.id,
            e.severity,
            e.error_type,
            e.error_message,
            e.endpoint,
            e.method,
            e.status,
            e.user.name if e.user else 'Anonymous',
            e.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            e.traceback
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=error_logs.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/api/donations')
@login_required
def get_donations():
    donations = Donation.query.filter_by(status='available').order_by(Donation.created_at.desc()).all()
    return jsonify([{
        'id': d.id,
        'foodName': d.food_name,
        'foodType': d.food_type,
        'foodCategory': d.food_category,
        'quantity': d.quantity,
        'urgency': d.urgency,
        'expiry': d.expiry.isoformat(),
        'address': d.address,
        'pickupLocation': d.pickup_location,
        'phone': d.phone,
        'pickupTime': d.pickup_time,
        'createdAt': d.created_at.isoformat(),
        'donorName': d.donor.name
    } for d in donations])

@app.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id).update({'read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get(notif_id)
    if notif and notif.user_id == current_user.id:
        notif.read = True
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/rating/submit', methods=['POST'])
@login_required
def submit_rating():
    if current_user.role != 'receiver':
        return jsonify({'success': False, 'message': 'Only receivers can submit ratings'}), 403
    
    data = request.json
    donation_id = data.get('donation_id')
    rating_value = data.get('rating')
    feedback_text = data.get('feedback', '').strip()
    
    if not rating_value or rating_value < 1 or rating_value > 5:
        return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400
    
    donation = Donation.query.get(donation_id)
    if not donation:
        return jsonify({'success': False, 'message': 'Donation not found'}), 404
    
    if donation.status != 'completed':
        return jsonify({'success': False, 'message': 'Can only rate completed donations'}), 400
    
    if donation.claimed_by != current_user.id:
        return jsonify({'success': False, 'message': 'You can only rate donations you claimed'}), 403
    
    existing_rating = DonorRating.query.filter_by(
        donation_id=donation_id,
        receiver_id=current_user.id
    ).first()
    
    if existing_rating:
        return jsonify({'success': False, 'message': 'You have already rated this donation'}), 400
    
    new_rating = DonorRating(
        donation_id=donation_id,
        donor_id=donation.donor_id,
        receiver_id=current_user.id,
        rating=rating_value,
        feedback=feedback_text if feedback_text else None
    )
    
    db.session.add(new_rating)
    db.session.commit()
    
    add_notification(donation.donor_id, 
        f'You received a {rating_value}⭐ rating from {current_user.org_name or current_user.name}!')
    
    return jsonify({'success': True, 'message': 'Rating submitted successfully'})

@app.route('/api/donor/<int:donor_id>/ratings', methods=['GET'])
def get_donor_ratings(donor_id):
    ratings = DonorRating.query.filter_by(donor_id=donor_id).order_by(DonorRating.created_at.desc()).all()
    
    if not ratings:
        return jsonify({
            'average_rating': None,
            'total_ratings': 0,
            'ratings': []
        })
    
    average = sum(r.rating for r in ratings) / len(ratings)
    
    return jsonify({
        'average_rating': round(average, 1),
        'total_ratings': len(ratings),
        'ratings': [{
            'rating': r.rating,
            'feedback': r.feedback,
            'receiver_name': r.receiver.org_name or r.receiver.name,
            'created_at': r.created_at.isoformat()
        } for r in ratings]
    })

with app.app_context():
    db.create_all()
    try:
        from db_utils import check_and_update_schema
        check_and_update_schema(app)
    except Exception as e:
        print(f"Warning: Auto-migration failed: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8500)
