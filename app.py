import os
import random
import string
import io
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import json
from concurrent.futures import ThreadPoolExecutor

# Create a base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "hydrogen_credits_dev_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with SQLAlchemy
db.init_app(app)

# Import models after db initialization to avoid circular imports
with app.app_context():
    from models import User, HydrogenCredit, Transaction, CreditCertification, PartnershipCredit, TradingBid, Notification, MarketAnalytics
    db.create_all()

# Initialize thread pool executor for concurrent operations
executor = ThreadPoolExecutor(max_workers=4)

# Threading functions for buy/sell operations
def process_buy_transaction(credit_id, buyer_id, price, quantity):
    """Process buy transaction in a separate thread"""
    try:
        with app.app_context():
            credit = HydrogenCredit.query.get(credit_id)
            buyer = User.query.get(buyer_id)
            seller = User.query.get(credit.owner_id)
            
            if not credit or not credit.is_for_sale or credit.owner_id == buyer_id:
                return {"success": False, "message": "Credit not available for purchase"}
            
            # Create transaction
            transaction = Transaction(
                credit_id=credit_id,
                buyer_id=buyer_id,
                seller_id=credit.owner_id,
                price=price,
                quantity=quantity,
                timestamp=datetime.now(),
                transaction_type='purchase',
                status='completed'
            )
            
            # Update credit ownership
            credit.owner_id = buyer_id
            credit.is_for_sale = False
            
            # Update user totals
            buyer.total_offsets += quantity
            if hasattr(buyer, 'trading_volume'):
                buyer.trading_volume += price
            if hasattr(seller, 'trading_volume'):
                seller.trading_volume += price
            
            # Create notifications
            buyer_notification = Notification(
                user_id=buyer_id,
                title='Purchase Successful',
                message=f'You have successfully purchased {quantity} kg of hydrogen credits from {credit.project_name}',
                notification_type='trade',
                priority='normal',
                is_read=False
            )
            
            seller_notification = Notification(
                user_id=seller.id,
                title='Credit Sold',
                message=f'Your hydrogen credit from {credit.project_name} has been sold to {buyer.username}',
                notification_type='trade',
                priority='normal',
                is_read=False
            )
            
            db.session.add_all([transaction, buyer_notification, seller_notification])
            db.session.commit()
            
            return {"success": True, "message": "Purchase completed successfully!", "transaction_id": transaction.id}
            
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Transaction failed: {str(e)}"}

def process_sell_listing(credit_id, seller_id, price):
    """Process sell listing in a separate thread"""
    try:
        with app.app_context():
            credit = HydrogenCredit.query.get(credit_id)
            
            if not credit or credit.owner_id != seller_id or credit.is_retired:
                return {"success": False, "message": "Credit not available for listing"}
            
            # Update credit for sale
            credit.is_for_sale = True
            credit.price = price
            credit.min_bid_price = price * 0.9  # Set minimum bid to 90% of asking price
            
            # Create notification
            notification = Notification(
                user_id=seller_id,
                title='Credit Listed for Sale',
                message=f'Your hydrogen credit from {credit.project_name} is now listed for ${price:.2f}',
                notification_type='trade',
                priority='normal',
                is_read=False
            )
            
            db.session.add(notification)
            db.session.commit()
            
            return {"success": True, "message": f"Credit listed for sale at ${price:.2f}"}
            
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Listing failed: {str(e)}"}

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        wallet_address = request.form.get('wallet_address')
        username = request.form.get('username')
        
        # Validate input
        if not wallet_address or not username:
            flash('Please provide both username and wallet address', 'error')
            return redirect(url_for('login'))
        
        # Validate wallet address format (basic Ethereum address validation)
        if not wallet_address.startswith('0x') or len(wallet_address) != 42:
            flash('Invalid wallet address format', 'error')
            return redirect(url_for('login'))
        
        # Check if user exists
        user = User.query.filter_by(wallet_address=wallet_address.lower()).first()
        
        if not user:
            # Create new user
            user = User(
                username=username,
                wallet_address=wallet_address.lower(),
                is_verified=True,
                registration_date=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully!', 'success')
        else:
            flash('Welcome back!', 'success')
        
        # Set user session
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get user's hydrogen credits and transactions
    owned_credits = HydrogenCredit.query.filter_by(owner_id=user_id).all()
    transactions = Transaction.query.filter(
        (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    # Get notifications
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          user=user, 
                          owned_credits=owned_credits,
                          transactions=transactions,
                          notifications=notifications)

@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    # Get all available hydrogen credits for sale
    available_credits = HydrogenCredit.query.filter_by(is_for_sale=True, is_retired=False).all()
    
    # Calculate marketplace stats
    total_credits = len(available_credits)
    total_retired = HydrogenCredit.query.filter_by(is_retired=True).count()
    project_count = db.session.query(HydrogenCredit.project_name).distinct().count()
    
    # Calculate average price if credits exist
    avg_price = 0
    if total_credits > 0:
        avg_price = sum(credit.price for credit in available_credits) / total_credits
    
    stats = {
        'total_credits': f"{total_credits:,}",
        'total_retired': f"{total_retired:,}",
        'project_count': project_count,
        'avg_price': f"${avg_price:.2f}"
    }
    
    return render_template('marketplace.html', available_credits=available_credits, stats=stats)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Get user's hydrogen credits and transactions
    owned_credits = HydrogenCredit.query.filter_by(owner_id=user_id).all()
    transactions = Transaction.query.filter(
        (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
    ).order_by(Transaction.timestamp.desc()).all()
    
    return render_template('profile.html', 
                          user=user, 
                          owned_credits=owned_credits,
                          transactions=transactions)

@app.route('/partnerships')
def partnerships():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Get active partnerships
    active_partnerships = PartnershipCredit.query.filter_by(
        partner_id=session['user_id'], 
        status='active'
    ).all()
    
    # Get available partnership opportunities
    available_partnerships = HydrogenCredit.query.filter_by(
        is_partnership=True,
        is_retired=False
    ).all()
    
    return render_template('partnerships.html', 
                          user=user,
                          active_partnerships=active_partnerships,
                          available_partnerships=available_partnerships)

# API Routes
@app.route('/api/credits', methods=['GET'])
def get_credits():
    available_credits = HydrogenCredit.query.filter_by(is_for_sale=True, is_retired=False).all()
    credits_data = []
    
    for credit in available_credits:
        credits_data.append({
            'id': credit.id,
            'token_id': credit.token_id,
            'project_name': credit.project_name,
            'quantity': credit.quantity,
            'price': credit.price,
            'vintage_year': credit.vintage_year,
            'certification': credit.certification,
            'project_type': credit.project_type,
            'owner_id': credit.owner_id
        })
    
    return jsonify({"credits": credits_data})

@app.route('/api/buy', methods=['POST'])
def buy_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    credit_id = data.get('credit_id')
    
    if not credit_id:
        return jsonify({"success": False, "message": "Credit ID is required"}), 400
    
    credit = HydrogenCredit.query.get(credit_id)
    if not credit:
        return jsonify({"success": False, "message": "Credit not found"}), 404
    
    if credit.owner_id == session['user_id']:
        return jsonify({"success": False, "message": "Cannot buy your own credit"}), 400
    
    if not credit.is_for_sale or credit.is_retired:
        return jsonify({"success": False, "message": "Credit not available for sale"}), 400
    
    # Process transaction asynchronously
    future = executor.submit(process_buy_transaction, credit_id, session['user_id'], credit.price, credit.quantity)
    result = future.result(timeout=30)  # 30 second timeout
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/api/sell', methods=['POST'])
def sell_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    credit_id = data.get('credit_id')
    price = data.get('price')
    
    if not credit_id or not price:
        return jsonify({"success": False, "message": "Credit ID and price are required"}), 400
    
    try:
        price = float(price)
        if price <= 0:
            return jsonify({"success": False, "message": "Price must be greater than 0"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid price format"}), 400
    
    # Process listing asynchronously
    future = executor.submit(process_sell_listing, credit_id, session['user_id'], price)
    result = future.result(timeout=30)  # 30 second timeout
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/api/retire', methods=['POST'])
def retire_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    credit_id = data.get('credit_id')
    
    if not credit_id:
        return jsonify({"success": False, "message": "Credit ID is required"}), 400
    
    credit = HydrogenCredit.query.get(credit_id)
    if not credit:
        return jsonify({"success": False, "message": "Credit not found"}), 404
    
    if credit.owner_id != session['user_id']:
        return jsonify({"success": False, "message": "You do not own this credit"}), 403
    
    try:
        credit.is_retired = True
        credit.is_for_sale = False
        credit.retirement_date = datetime.now()
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Credit retired successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/connect-wallet', methods=['POST'])
def connect_wallet():
    data = request.get_json()
    wallet_address = data.get('wallet_address')
    username = data.get('username', 'User')
    
    if not wallet_address:
        return jsonify({"success": False, "message": "Wallet address is required"}), 400
    
    # Validate wallet address format
    if not wallet_address.startswith('0x') or len(wallet_address) != 42:
        return jsonify({"success": False, "message": "Invalid wallet address format"}), 400
    
    try:
        # Check if user exists
        user = User.query.filter_by(wallet_address=wallet_address.lower()).first()
        
        if not user:
            # Create new user
            user = User(
                username=username,
                wallet_address=wallet_address.lower(),
                is_verified=True,
                registration_date=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
        
        # Set user session
        session['user_id'] = user.id
        
        return jsonify({
            "success": True, 
            "message": "Wallet connected successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "wallet_address": user.wallet_address
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/place-bid', methods=['POST'])
def place_bid():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    credit_id = data.get('credit_id')
    bid_price = data.get('bid_price')
    quantity = data.get('quantity')
    
    if not all([credit_id, bid_price, quantity]):
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    try:
        bid_price = float(bid_price)
        quantity = float(quantity)
        
        if bid_price <= 0 or quantity <= 0:
            return jsonify({"success": False, "message": "Price and quantity must be greater than 0"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid price or quantity format"}), 400
    
    credit = HydrogenCredit.query.get(credit_id)
    if not credit:
        return jsonify({"success": False, "message": "Credit not found"}), 404
    
    if credit.owner_id == session['user_id']:
        return jsonify({"success": False, "message": "Cannot bid on your own credit"}), 400
    
    try:
        bid = TradingBid(
            credit_id=credit_id,
            user_id=session['user_id'],
            bid_price=bid_price,
            quantity_desired=quantity,
            bid_type='buy',
            status='active',
            expiry_date=datetime.now() + timedelta(days=7),
            notes=data.get('notes', '')
        )
        
        db.session.add(bid)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Bid placed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    notification = Notification.query.filter_by(id=notification_id, user_id=session['user_id']).first()
    if not notification:
        return jsonify({"success": False, "message": "Notification not found"}), 404
    
    try:
        notification.is_read = True
        db.session.commit()
        return jsonify({"success": True, "message": "Notification marked as read"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
