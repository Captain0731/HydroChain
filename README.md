# Overview

HydroChain is a decentralized marketplace for trading verified hydrogen credits, built as a Flask web application. The platform enables users to buy, sell, and track hydrogen offset credits through a blockchain-integrated trading system. The application serves as a marketplace where hydrogen producers can list their verified credits and buyers can purchase them for carbon offset purposes. The system includes user verification, credit certification tracking, partnership programs for bulk trading, and integration with MetaMask wallets for secure transactions.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework Architecture
The application is built using Flask as the primary web framework with a traditional MVC pattern. The application uses SQLAlchemy ORM for database interactions and Jinja2 templating for server-side rendering. The architecture follows a modular design with separate files for models, database seeding, and main application logic. The system uses ProxyFix middleware for proper handling of proxy headers in production environments.

## Database Design
The system uses SQLAlchemy ORM with PostgreSQL as the primary database (configured via DATABASE_URL environment variable). The data model consists of multiple interconnected entities:

- **User**: Stores user profiles with wallet addresses, verification status, company information, and trading statistics
- **HydrogenCredit**: Represents tradeable credits with detailed project information, quantities (in kg H2), pricing, vintage years, certification standards, and blockchain token IDs
- **Transaction**: Records all credit transfers between users with timestamps, quantities, and pricing information
- **PartnershipCredit**: Manages bulk trading agreements and long-term partnerships
- **TradingBid**: Handles bidding system for credit purchases
- **Notification**: User notification system for trading activities
- **MarketAnalytics**: Market data and statistics tracking

The database relationships use foreign keys enabling proper transaction history tracking, credit ownership management, and comprehensive user activity monitoring.

## Authentication and Session Management
User authentication is designed around Ethereum wallet addresses rather than traditional passwords. The system stores wallet addresses as unique identifiers and includes multiple verification levels (basic, verified, premium, enterprise). Flask sessions are used for user state management with configurable secret keys from environment variables. The system supports both MetaMask integration and manual wallet address login.

## Frontend Architecture
The frontend uses Bootstrap 5 for responsive design with a custom dark theme featuring blue and green accents. The design includes custom CSS variables for theming, JavaScript modules for Web3 wallet connectivity, and dynamic marketplace interactions. The interface supports theme toggling, keyboard shortcuts, and real-time updates for trading activities.

## Concurrency and Threading
The application implements ThreadPoolExecutor for handling concurrent buy/sell operations. This allows multiple trading transactions to be processed simultaneously without blocking the main application thread. The threading system is designed to handle high-volume trading scenarios with proper error handling and transaction integrity.

## Data Seeding System
A comprehensive seeding module populates the database with realistic sample data including various hydrogen production methods (electrolysis, steam reforming, biomass gasification), multiple certification standards (Green Hydrogen Standard, CertifHy), and global project locations. This provides a realistic testing environment and demonstration data.

# External Dependencies

## Frontend Libraries
- **Bootstrap 5.3.0**: Responsive UI framework providing layout components, form controls, and utility classes
- **Font Awesome 6.4.0**: Icon library providing consistent iconography throughout the interface
- **Google Fonts (Inter)**: Modern typography system for clean, readable text rendering
- **Web3.js 1.8.0**: Blockchain interaction library enabling MetaMask wallet connectivity and Ethereum network communication

## Backend Framework and Database
- **Flask 3.0.3**: Core web application framework handling routing, templating, and request processing
- **Flask-SQLAlchemy 3.1.1**: Database ORM integration providing model definitions and query capabilities
- **SQLAlchemy 2.0.35**: Database abstraction layer with advanced ORM features and relationship management
- **Werkzeug 3.0.4**: WSGI utilities, development server, and security functions including password hashing
- **PostgreSQL**: Primary production database (configured via DATABASE_URL environment variable)

## Blockchain and Web3 Integration
- **MetaMask**: Browser extension wallet for Ethereum transaction signing and account management
- **Ethereum Network**: Blockchain network for token management and transaction verification (supports multiple networks including mainnet and testnets)
- **Web3 Provider**: JavaScript library enabling blockchain connectivity and smart contract interactions

## Development and Deployment
- **Environment Variables**: Configuration management for database URLs, session secrets, and deployment settings
- **ThreadPoolExecutor**: Python concurrent futures for handling parallel trading operations
- **Logging**: Debug logging system for development and production monitoring
