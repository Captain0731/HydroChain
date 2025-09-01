"""
Seed script to populate the database with sample hydrogen credits
"""
import os
import sys
from datetime import datetime, timedelta
from random import randint, uniform, choice

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, HydrogenCredit, Transaction, CreditCertification, PartnershipCredit, TradingBid, Notification, MarketAnalytics

# Sample data
certifications = [
    "Green Hydrogen Standard", "CertifHy", "TÜV SÜD Green Hydrogen", 
    "Low Carbon Hydrogen Standard", "Renewable Hydrogen Certificate"
]

certification_levels = ["standard", "premium", "verified", "certified"]
partnership_types = ["corporate_bulk", "long_term", "exclusive", "renewable_only"]
verification_companies = ["TÜV SÜD", "DNV GL", "SGS", "Bureau Veritas", "Green Hydrogen Council"]

project_types = [
    "Electrolysis", "Steam Reforming", "Biomass Gasification",
    "Solar Thermochemical", "Wind-Powered Electrolysis", "Nuclear Electrolysis",
    "Photobiological Production"
]

countries = [
    "Germany", "Netherlands", "Japan", "Australia", "Chile", 
    "Norway", "Denmark", "United States", "Canada", "South Korea"
]

project_names = [
    "NorthSea Green H2 Plant", "Solar Hydrogen Australia", "WindH2 Netherlands",
    "Nordic Electrolysis Hub", "Patagonia H2 Project", "Rhine Valley Hydrogen",
    "Baltic Sea Wind-to-H2", "Sahara Solar Hydrogen", "Arctic Green Energy",
    "Mediterranean H2 Initiative", "Pacific Rim Hydrogen", "Alpine Clean H2",
    "Desert Solar Electrolysis", "Offshore Wind H2", "Geothermal Hydrogen Plant",
    "Industrial H2 Cluster", "Green Valley Project", "Ocean Energy H2",
    "Mountain Peak Electrolysis", "Coastal Wind Hydrogen", "Urban H2 Network",
    "Rural Electrolysis Farm", "Hydropower H2 Station", "Biomass-to-H2 Plant"
]

def create_project_name():
    """Create unique project name combinations"""
    project_type = choice(project_types)
    country = choice(countries)
    
    if randint(0, 1):
        return f"{project_type} Plant in {country}"
    else:
        return f"{country} {project_type} Hub"

def seed_database():
    """Seed the database with sample data"""
    print("Starting database seeding...")
    
    with app.app_context():
        # Create admin user if not exists
        admin = User.query.filter_by(wallet_address="0x742d35cc6634c0532925a3b844bc454e4438f44e").first()
        if not admin:
            admin = User(
                username="admin",
                wallet_address="0x742d35cc6634c0532925a3b844bc454e4438f44e",
                email="admin@hydrochain.com",
                company_name="HydroChain Ltd",
                is_verified=True,
                is_partner=True,
                verification_level="enterprise",
                registration_date=datetime.now() - timedelta(days=30),
                total_offsets=0.0,
                trading_volume=0.0,
                reputation_score=5.0
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin user with ID: {admin.id}")
        
        # Check if we already have credits
        existing_count = HydrogenCredit.query.count()
        if existing_count >= 21:
            print(f"Database already has {existing_count} hydrogen credits. Skipping seeding.")
            return
        
        # Create 21 hydrogen credits
        print("Creating 21 hydrogen credits...")
        
        hydrogen_credits = []
        for i in range(1, 22):
            # Use a predefined project name if available, otherwise generate one
            if i <= len(project_names):
                project_name = project_names[i-1]
            else:
                project_name = create_project_name()
                
            # Random data for the hydrogen credit
            vintage_year = randint(2020, 2025)
            quantity = round(uniform(100, 5000), 1)  # Between 100 and 5000 kg
            price = round(uniform(2.5, 8.0), 2)   # Between $2.50 and $8.00 per kg
            
            # Enhanced hydrogen credit data
            is_partnership = randint(0, 1) == 1 if i <= 5 else False  # First 5 could be partnerships
            
            hydrogen_credit = HydrogenCredit(
                token_id=i,
                project_name=project_name,
                quantity=quantity,
                price=price,
                min_bid_price=price * 0.9,  # 10% below asking price
                vintage_year=vintage_year,
                certification=choice(certifications),
                certification_level=choice(certification_levels),
                project_type=choice(project_types),
                project_country=choice(countries),
                project_region=f"{choice(countries)} Region",
                environmental_impact=round(quantity * uniform(2.0, 4.0), 1),  # CO2 reduction
                quality_rating=round(uniform(3.0, 5.0), 1),
                is_for_sale=True,
                is_retired=False,
                is_partnership=is_partnership,
                issue_date=datetime.now() - timedelta(days=randint(30, 365)),
                expiry_date=datetime.now() + timedelta(days=randint(365, 1095)),  # 1-3 years
                owner_id=admin.id
            )
            hydrogen_credits.append(hydrogen_credit)
        
        # Add all credits to the database
        db.session.add_all(hydrogen_credits)
        db.session.commit()
        
        print(f"Successfully added 21 hydrogen credits to the database")
        
        # Create sample certifications for some credits
        print("Adding sample certifications...")
        sample_credits = hydrogen_credits[:5]  # First 5 credits get certifications
        
        for i, credit in enumerate(sample_credits):
            certification = CreditCertification(
                credit_id=credit.id,
                certifier_name=choice(verification_companies),
                certification_type=choice(["verification", "audit", "compliance"]),
                certificate_number=f"HC-{randint(100000, 999999)}",
                issue_date=datetime.now() - timedelta(days=randint(10, 180)),
                expiry_date=datetime.now() + timedelta(days=randint(365, 730)),
                status="active",
                confidence_score=round(uniform(75.0, 95.0), 1)
            )
            db.session.add(certification)
        
        # Create sample partnership credits
        print("Adding sample partnerships...")
        partnership_credits = [c for c in hydrogen_credits if c.is_partnership][:3]
        
        for credit in partnership_credits:
            partnership = PartnershipCredit(
                credit_id=credit.id,
                partner_id=admin.id,
                partnership_type=choice(partnership_types),
                allocated_quantity=credit.quantity * uniform(0.3, 0.8),
                reserved_price=credit.price * uniform(0.85, 0.95),
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=randint(90, 365)),
                auto_renew=choice([True, False]),
                status="active",
                terms_conditions="Standard partnership terms apply"
            )
            db.session.add(partnership)
        
        # Create sample trading bids
        print("Adding sample trading bids...")
        sample_credits_for_bids = hydrogen_credits[5:8]  # Credits 6-8 get bids
        
        for credit in sample_credits_for_bids:
            bid = TradingBid(
                credit_id=credit.id,
                user_id=admin.id,
                bid_price=credit.price * uniform(0.8, 1.1),
                quantity_desired=credit.quantity * uniform(0.5, 1.0),
                bid_type="buy",
                status="active",
                expiry_date=datetime.now() + timedelta(hours=randint(24, 168)),  # 1-7 days
                notes=f"Interested in bulk purchase of {credit.project_type} credits"
            )
            db.session.add(bid)
        
        # Create sample notifications
        print("Adding sample notifications...")
        notifications = [
            Notification(
                user_id=admin.id,
                title="Welcome to HydroChain",
                message="Welcome to the hydrogen credit marketplace! Connect your MetaMask wallet to start trading verified credits today.",
                notification_type="system",
                priority="normal",
                is_read=False
            ),
            Notification(
                user_id=admin.id,
                title="New Credit Available",
                message="A new hydrogen credit from Nordic Electrolysis Hub is now available for purchase.",
                notification_type="trade",
                priority="normal",
                is_read=False
            ),
            Notification(
                user_id=admin.id,
                title="Partnership Opportunity",
                message="Corporate bulk partnership available for renewable energy credits.",
                notification_type="partnership",
                priority="high",
                is_read=False
            )
        ]
        
        db.session.add_all(notifications)
        
        # Create sample market analytics
        print("Adding market analytics...")
        analytics = MarketAnalytics(
            date=datetime.now().date(),
            total_credits_traded=15,
            total_volume_kg=sum(c.quantity for c in hydrogen_credits[:15]),
            total_value_usd=sum(c.price for c in hydrogen_credits[:15]),
            avg_price_per_kg=sum(c.price for c in hydrogen_credits) / len(hydrogen_credits),
            active_users=1,
            new_partnerships=len(partnership_credits),
            market_volatility=round(uniform(0.05, 0.15), 3)
        )
        db.session.add(analytics)
        
        db.session.commit()
        print(f"Successfully seeded database with enhanced features!")

if __name__ == "__main__":
    seed_database()
