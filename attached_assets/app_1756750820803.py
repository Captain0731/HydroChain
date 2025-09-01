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
                transaction_type='purchase'
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
                user_id=credit.owner_id,
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
    ).order_by(Transaction.timestamp.desc()).all()
    
    return render_template('dashboard.html', 
                          user=user, 
                          owned_credits=owned_credits,
                          transactions=transactions)

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



@app.route('/api/retire', methods=['POST'])
def retire_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    credit_id = request.json.get('credit_id')
    
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

@app.route('/connect-wallet', methods=['POST'])
def connect_wallet():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    wallet_address = request.json.get('wallet_address')
    if not wallet_address:
        return jsonify({"success": False, "message": "Wallet address is required"}), 400
    
    try:
        user = User.query.get(session['user_id'])
        user.wallet_address = wallet_address.lower()
        db.session.commit()
        return jsonify({"success": True, "message": "Wallet connected successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Partnership Credit Routes
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


# Trading Bid Routes
@app.route('/api/place-bid', methods=['POST'])
def place_bid():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.json
    credit_id = data.get('credit_id')
    bid_price = float(data.get('bid_price', 0))
    quantity = float(data.get('quantity', 0))
    expiry_hours = int(data.get('expiry_hours', 24))
    
    if not all([credit_id, bid_price, quantity]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    try:
        bid = TradingBid(
            credit_id=credit_id,
            user_id=session['user_id'],
            bid_price=bid_price,
            quantity_desired=quantity,
            expiry_date=datetime.now() + timedelta(hours=expiry_hours),
            status='active'
        )
        
        db.session.add(bid)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Bid placed successfully", "bid_id": bid.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/accept-bid', methods=['POST'])
def accept_bid():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    bid_id = request.json.get('bid_id')
    if not bid_id:
        return jsonify({"success": False, "message": "Bid ID required"}), 400
    
    bid = TradingBid.query.get(bid_id)
    if not bid:
        return jsonify({"success": False, "message": "Bid not found"}), 404
    
    credit = HydrogenCredit.query.get(bid.credit_id)
    if credit.owner_id != session['user_id']:
        return jsonify({"success": False, "message": "You don't own this credit"}), 403
    
    try:
        # Create transaction
        transaction = Transaction(
            credit_id=bid.credit_id,
            buyer_id=bid.user_id,
            seller_id=session['user_id'],
            price=bid.bid_price,
            quantity=bid.quantity_desired,
            transaction_type='bid',
            status="completed"
        )
        
        # Update credit ownership
        credit.owner_id = bid.user_id
        credit.is_for_sale = False
        
        # Update bid status
        bid.status = 'accepted'
        bid.accepted_at = datetime.now()
        
        # Update buyer's total offsets
        buyer = User.query.get(bid.user_id)
        buyer.total_offsets += bid.quantity_desired
        
        # Create notifications
        buyer_notification = Notification(
            user_id=bid.user_id,
            title="Bid Accepted",
            message=f"Your bid for {credit.project_name} has been accepted!",
            notification_type="trade"
        )
        
        seller_notification = Notification(
            user_id=session['user_id'],
            title="Credit Sold",
            message=f"You sold {credit.project_name} for ${bid.bid_price}",
            notification_type="trade"
        )
        
        db.session.add_all([transaction, buyer_notification, seller_notification])
        db.session.commit()
        
        return jsonify({"success": True, "message": "Bid accepted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Certification Routes
@app.route('/api/add-certification', methods=['POST'])
def add_certification():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.json
    credit_id = data.get('credit_id')
    certifier = data.get('certifier_name')
    cert_type = data.get('certification_type')
    cert_number = data.get('certificate_number')
    
    if not all([credit_id, certifier, cert_type, cert_number]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    credit = HydrogenCredit.query.get(credit_id)
    if not credit or credit.owner_id != session['user_id']:
        return jsonify({"success": False, "message": "Credit not found or not owned"}), 404
    
    try:
        certification = CreditCertification(
            credit_id=credit_id,
            certifier_name=certifier,
            certification_type=cert_type,
            certificate_number=cert_number,
            confidence_score=85.0  # Default confidence score
        )
        
        # Upgrade credit certification level
        if cert_type == 'audit':
            credit.certification_level = 'verified'
        elif cert_type == 'compliance':
            credit.certification_level = 'certified'
        
        db.session.add(certification)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Certification added successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Notification Routes
@app.route('/api/notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(
        Notification.created_at.desc()
    ).limit(20).all()
    
    notification_data = []
    for notif in notifications:
        notification_data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'type': notif.notification_type,
            'priority': notif.priority,
            'is_read': notif.is_read,
            'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M'),
            'action_url': notif.action_url
        })
    
    return jsonify({"notifications": notification_data})

@app.route('/api/mark-notification-read', methods=['POST'])
def mark_notification_read():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    notification_id = request.json.get('notification_id')
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=session['user_id']
    ).first()
    
    if not notification:
        return jsonify({"success": False, "message": "Notification not found"}), 404
    
    try:
        notification.is_read = True
        db.session.commit()
        return jsonify({"success": True, "message": "Notification marked as read"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Analytics Routes
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    # Portfolio analytics
    user = User.query.get(session['user_id'])
    credits = HydrogenCredit.query.filter_by(owner_id=session['user_id']).all()
    transactions = Transaction.query.filter(
        (Transaction.buyer_id == session['user_id']) | (Transaction.seller_id == session['user_id'])
    ).all()
    
    # Calculate analytics
    total_investment = sum(t.price for t in transactions if t.buyer_id == session['user_id'])
    total_sales = sum(t.price for t in transactions if t.seller_id == session['user_id'])
    
    analytics_data = {
        'total_credits': len(credits),
        'total_investment': total_investment,
        'total_sales': total_sales,
        'net_position': total_sales - total_investment,
        'avg_credit_price': sum(c.price for c in credits) / len(credits) if credits else 0,
        'portfolio_value': sum(c.price for c in credits if not c.is_retired)
    }
    
    return render_template('analytics.html', user=user, analytics=analytics_data, transactions=transactions)

# API Endpoints
@app.route('/api/create-certificate', methods=['POST'])
def api_create_certificate():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        
        # Generate next token ID
        max_token = db.session.query(db.func.max(HydrogenCredit.token_id)).scalar() or 0
        next_token_id = max_token + 1
        
        # Create new hydrogen credit certificate
        credit = HydrogenCredit(
            token_id=next_token_id,
            project_name=data.get('project_name'),
            quantity=float(data.get('quantity')),
            price=float(data.get('price')),
            min_bid_price=float(data.get('price')) * 0.9,  # Default 10% below asking price
            vintage_year=int(data.get('vintage_year')),
            certification=data.get('certification'),
            certification_level=data.get('certification_level'),
            project_type=data.get('project_type'),
            project_country=data.get('project_country'),
            project_region=data.get('project_region', ''),
            environmental_impact=float(data.get('environmental_impact', 0)),
            quality_rating=float(data.get('quality_rating', 4.0)),
            is_for_sale=data.get('is_for_sale', False),
            is_partnership=data.get('is_partnership', False),
            is_retired=False,
            issue_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=1095),  # 3 years validity
            owner_id=session['user_id']
        )
        
        db.session.add(credit)
        db.session.commit()
        
        # Update user's total offsets
        user = User.query.get(session['user_id'])
        user.total_offsets += credit.quantity
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Certificate created successfully! Token ID: {next_token_id}",
            "credit_id": credit.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error creating certificate: {str(e)}"}), 500

@app.route('/api/place-bid', methods=['POST'])
def api_place_bid():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        credit_id = data.get('credit_id')
        bid_price = float(data.get('bid_price'))
        quantity_desired = float(data.get('quantity_desired'))
        expiry_hours = int(data.get('expiry_hours'))
        notes = data.get('notes', '')
        
        # Validate credit exists and is for sale
        credit = HydrogenCredit.query.get(credit_id)
        if not credit or not credit.is_for_sale:
            return jsonify({"success": False, "message": "Credit not available"}), 400
        
        # Validate minimum bid price
        min_bid = credit.min_bid_price or credit.price * 0.9
        if bid_price < min_bid:
            return jsonify({"success": False, "message": f"Bid must be at least ${min_bid:.2f}"}), 400
        
        # Create the bid
        bid = TradingBid(
            credit_id=credit_id,
            user_id=session['user_id'],
            bid_price=bid_price,
            quantity_desired=quantity_desired,
            bid_type='buy',
            status='active',
            expiry_date=datetime.now() + timedelta(hours=expiry_hours),
            notes=notes
        )
        
        db.session.add(bid)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Bid placed successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error placing bid: {str(e)}"}), 500

@app.route('/api/sell-credit', methods=['POST'])
def sell_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    credit_id = request.json.get('credit_id')
    price = request.json.get('price')
    
    if not credit_id or not price:
        return jsonify({"success": False, "message": "Credit ID and price are required"}), 400
    
    try:
        # Use threading for sell listing
        future = executor.submit(process_sell_listing, credit_id, session['user_id'], float(price))
        result = future.result(timeout=10)  # 10 second timeout
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/buy-credit', methods=['POST'])
def buy_credit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    credit_id = request.json.get('credit_id')
    
    if not credit_id:
        return jsonify({"success": False, "message": "Credit ID is required"}), 400
    
    try:
        # Get credit details for price and quantity
        credit = HydrogenCredit.query.get(credit_id)
        if not credit or not credit.is_for_sale:
            return jsonify({"success": False, "message": "Credit not available for purchase"}), 404
        
        # Use threading for buy transaction
        future = executor.submit(process_buy_transaction, credit_id, session['user_id'], credit.price, credit.quantity)
        result = future.result(timeout=15)  # 15 second timeout
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/create-partnership', methods=['POST'])
def create_partnership():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        credit_id = data.get('credit_id')
        partnership_type = data.get('partnership_type')
        quantity = float(data.get('quantity', 0))
        price = float(data.get('price', 0))
        duration_days = int(data.get('duration_days', 30))
        
        if not all([credit_id, partnership_type, quantity, price]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Validate credit exists
        credit = HydrogenCredit.query.get(credit_id)
        if not credit:
            return jsonify({"success": False, "message": "Credit not found"}), 400
        
        # Check if user is eligible for partnerships
        user = User.query.get(session['user_id'])
        if not user.is_verified:
            return jsonify({"success": False, "message": "Account must be verified for partnerships"}), 400
        
        # Create partnership request
        partnership = PartnershipCredit(
            credit_id=credit_id,
            partner_id=session['user_id'],
            partnership_type=partnership_type,
            allocated_quantity=quantity,
            reserved_price=price,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            auto_renew=False,
            status='pending',
            terms_conditions='Partnership request pending approval'
        )
        
        db.session.add(partnership)
        
        # Create notification for credit owner
        notification = Notification(
            user_id=credit.owner_id,
            title='New Partnership Request',
            message=f'{user.username} has requested a partnership for {credit.project_name}',
            notification_type='partnership',
            priority='normal',
            is_read=False
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Partnership request sent successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error creating partnership: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
