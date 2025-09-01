from app import db
from datetime import datetime, timedelta
from sqlalchemy import text

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    wallet_address = db.Column(db.String(42), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_partner = db.Column(db.Boolean, default=False)
    verification_level = db.Column(db.String(20), default='basic')  # basic, verified, premium, enterprise
    registration_date = db.Column(db.DateTime, default=datetime.now)
    total_offsets = db.Column(db.Float, default=0.0)  # Total hydrogen offset in kg
    trading_volume = db.Column(db.Float, default=0.0)
    reputation_score = db.Column(db.Float, default=5.0)
    
    # Relationships
    hydrogen_credits = db.relationship('HydrogenCredit', backref='owner', lazy=True, foreign_keys='HydrogenCredit.owner_id')
    purchases = db.relationship('Transaction', backref='buyer', lazy=True, foreign_keys='Transaction.buyer_id')
    sales = db.relationship('Transaction', backref='seller', lazy=True, foreign_keys='Transaction.seller_id')
    partnerships = db.relationship('PartnershipCredit', backref='partner', lazy=True, foreign_keys='PartnershipCredit.partner_id')
    bids = db.relationship('TradingBid', backref='bidder', lazy=True, foreign_keys='TradingBid.user_id')
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.id} - {self.username}>'

class HydrogenCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, nullable=False)  # Blockchain token ID
    project_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Amount in kg of H2
    price = db.Column(db.Float, nullable=False)  # Price per credit in USD
    min_bid_price = db.Column(db.Float, nullable=True)  # Minimum acceptable bid
    vintage_year = db.Column(db.Integer, nullable=False)  # Year the credit was generated
    certification = db.Column(db.String(50), nullable=False)  # e.g., Green Hydrogen Standard
    certification_level = db.Column(db.String(20), default='standard')  # standard, premium, verified, certified
    project_type = db.Column(db.String(50), nullable=False)  # e.g., Electrolysis, Steam Reforming
    project_country = db.Column(db.String(50), nullable=True)
    project_region = db.Column(db.String(100), nullable=True)
    environmental_impact = db.Column(db.Float, nullable=True)  # CO2 reduction in tons
    verification_documents = db.Column(db.Text, nullable=True)  # JSON array of document URLs
    quality_rating = db.Column(db.Float, default=3.0)  # 1-5 star rating
    is_for_sale = db.Column(db.Boolean, default=False)
    is_retired = db.Column(db.Boolean, default=False)
    is_partnership = db.Column(db.Boolean, default=False)
    issue_date = db.Column(db.DateTime, default=datetime.now)
    retirement_date = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # Foreign keys
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='credit', lazy=True)
    certifications = db.relationship('CreditCertification', backref='credit', lazy=True)
    bids = db.relationship('TradingBid', backref='credit', lazy=True)
    
    def __repr__(self):
        return f'<HydrogenCredit {self.id} - {self.project_name}, {self.quantity} kg>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey('hydrogen_credit.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)  # Transaction price in USD
    quantity = db.Column(db.Float, nullable=False)  # Amount in kg of H2
    transaction_type = db.Column(db.String(20), default='direct')  # direct, bid, partnership
    fees = db.Column(db.Float, default=0.0)  # Platform fees
    timestamp = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), nullable=False)  # pending, completed, failed, cancelled
    tx_hash = db.Column(db.String(66), nullable=True)  # Blockchain transaction hash
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Transaction {self.id} - {self.quantity} kg at ${self.price}>'

class CreditCertification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey('hydrogen_credit.id'), nullable=False)
    certifier_name = db.Column(db.String(100), nullable=False)  # e.g., TÜV SÜD, Green Hydrogen Council
    certification_type = db.Column(db.String(50), nullable=False)  # verification, audit, compliance
    certificate_number = db.Column(db.String(50), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.now)
    expiry_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, expired, revoked
    verification_url = db.Column(db.String(200), nullable=True)
    confidence_score = db.Column(db.Float, default=0.0)  # 0-100 confidence rating

    def __repr__(self):
        return f'<CreditCertification {self.certificate_number} - {self.certifier_name}>'

class PartnershipCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey('hydrogen_credit.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partnership_type = db.Column(db.String(30), nullable=False)  # corporate_bulk, long_term, exclusive
    allocated_quantity = db.Column(db.Float, nullable=False)
    reserved_price = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.now)
    end_date = db.Column(db.DateTime, nullable=False)
    auto_renew = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    terms_conditions = db.Column(db.Text, nullable=True)

    # Foreign Key Relationships
    credit = db.relationship('HydrogenCredit', backref='partnerships')
    
    def __repr__(self):
        return f'<PartnershipCredit {self.id} - {self.partnership_type}>'

class TradingBid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey('hydrogen_credit.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bid_price = db.Column(db.Float, nullable=False)
    quantity_desired = db.Column(db.Float, nullable=False)
    bid_type = db.Column(db.String(20), default='buy')  # buy, sell
    status = db.Column(db.String(20), default='active')  # active, accepted, rejected, expired
    expiry_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    accepted_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<TradingBid {self.id} - {self.bid_type} ${self.bid_price}>'

    @property
    def is_expired(self):
        return datetime.now() > self.expiry_date

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(30), nullable=False)  # trade, bid, partnership, system
    priority = db.Column(db.String(10), default='normal')  # low, normal, high, urgent
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    action_url = db.Column(db.String(200), nullable=True)
    extra_data = db.Column(db.Text, nullable=True)  # JSON data

    def __repr__(self):
        return f'<Notification {self.id} - {self.title}>'

class MarketAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.now().date)
    total_credits_traded = db.Column(db.Integer, default=0)
    total_volume_kg = db.Column(db.Float, default=0.0)
    total_value_usd = db.Column(db.Float, default=0.0)
    avg_price_per_kg = db.Column(db.Float, default=0.0)
    active_users = db.Column(db.Integer, default=0)
    new_partnerships = db.Column(db.Integer, default=0)
    market_volatility = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<MarketAnalytics {self.date} - ${self.avg_price_per_kg:.2f}/kg>'
