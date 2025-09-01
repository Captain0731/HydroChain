// HydroChain Main JavaScript Functions

// Global Variables
let currentUser = null;
let web3Instance = null;
let connectedAccount = null;

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkWalletConnection();
});

function initializeApp() {
    // Add fade-in animation to main content
    document.querySelector('main').classList.add('fade-in');
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Initialize popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
}

function setupEventListeners() {
    // Global wallet connect button
    const connectWalletBtn = document.getElementById('connectWalletBtn');
    if (connectWalletBtn) {
        connectWalletBtn.addEventListener('click', connectWallet);
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Auto-hide alerts
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            if (alert.classList.contains('alert-dismissible')) {
                const closeBtn = alert.querySelector('.btn-close');
                if (closeBtn) {
                    closeBtn.click();
                }
            }
        });
    }, 5000);
}

function handleKeyboardShortcuts(event) {
    // Ctrl/Cmd + K: Quick search (if implemented)
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        // Implement quick search functionality
        console.log('Quick search activated');
    }
    
    // Escape: Close modals
    if (event.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }
}

// Utility Functions
function showAlert(title, message, type = 'info', duration = 5000) {
    const alertContainer = createAlertContainer();
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertElement.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            <div>
                <strong>${title}</strong>
                <div>${message}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.appendChild(alertElement);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.classList.remove('show');
                setTimeout(() => {
                    if (alertElement.parentNode) {
                        alertElement.remove();
                    }
                }, 300);
            }
        }, duration);
    }
}

function createAlertContainer() {
    let container = document.getElementById('alert-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'alert-container';
        container.className = 'position-fixed top-0 start-50 translate-middle-x';
        container.style.zIndex = '9999';
        container.style.marginTop = '1rem';
        container.style.width = '90%';
        container.style.maxWidth = '500px';
        document.body.appendChild(container);
    }
    return container;
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function showLoading(message = 'Loading...', subtext = 'Please wait while we process your request') {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        document.getElementById('loadingText').textContent = message;
        document.getElementById('loadingSubtext').textContent = subtext;
        new bootstrap.Modal(modal).show();
    }
}

function hideLoading() {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        }
    }
}

// Wallet Functions
async function checkWalletConnection() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                connectedAccount = accounts[0];
                updateWalletStatus(connectedAccount);
            }
        } catch (error) {
            console.error('Error checking wallet connection:', error);
        }
    }
}

function updateWalletStatus(address) {
    const walletStatus = document.getElementById('walletStatus');
    const walletAddress = document.getElementById('walletAddress');
    
    if (walletStatus && walletAddress) {
        walletAddress.textContent = `${address.substring(0, 6)}...${address.substring(38)}`;
        walletStatus.classList.remove('d-none');
    }
    
    // Hide connect wallet button
    const connectBtn = document.getElementById('connectWalletBtn');
    if (connectBtn) {
        connectBtn.style.display = 'none';
    }
}

// API Helper Functions
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}

// Form Validation
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
        
        // Special validation for wallet addresses
        if (input.type === 'text' && input.name === 'wallet_address') {
            if (!isValidEthereumAddress(input.value)) {
                input.classList.add('is-invalid');
                isValid = false;
            }
        }
        
        // Email validation
        if (input.type === 'email' && input.value) {
            if (!isValidEmail(input.value)) {
                input.classList.add('is-invalid');
                isValid = false;
            }
        }
    });
    
    return isValid;
}

function isValidEthereumAddress(address) {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Copy to Clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showAlert('Copied', 'Text copied to clipboard', 'success', 2000);
        }).catch(err => {
            console.error('Failed to copy text:', err);
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showAlert('Copied', 'Text copied to clipboard', 'success', 2000);
    } catch (err) {
        console.error('Failed to copy text:', err);
        showAlert('Error', 'Failed to copy text', 'error', 3000);
    }
    
    document.body.removeChild(textArea);
}

// Local Storage Helpers
function saveToLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

function getFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Failed to read from localStorage:', error);
        return defaultValue;
    }
}

function removeFromLocalStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (error) {
        console.error('Failed to remove from localStorage:', error);
    }
}

// Format Helpers
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatNumber(number, decimals = 1) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };
    
    const config = { ...defaultOptions, ...options };
    return new Intl.DateTimeFormat('en-US', config).format(new Date(date));
}

function timeAgo(date) {
    const now = new Date();
    const past = new Date(date);
    const diffInSeconds = Math.floor((now - past) / 1000);
    
    const intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 },
        { label: 'second', seconds: 1 }
    ];
    
    for (const interval of intervals) {
        const count = Math.floor(diffInSeconds / interval.seconds);
        if (count >= 1) {
            return `${count} ${interval.label}${count > 1 ? 's' : ''} ago`;
        }
    }
    
    return 'Just now';
}

// Debounce Function
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Throttle Function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Network Status
function checkNetworkStatus() {
    const updateOnlineStatus = () => {
        if (!navigator.onLine) {
            showAlert('Offline', 'You are currently offline. Some features may not work.', 'warning', 0);
        } else {
            // Remove offline alerts
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                if (alert.textContent.includes('offline')) {
                    alert.remove();
                }
            });
        }
    };
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
}

// Initialize network status checking
checkNetworkStatus();

// Export functions for global use
window.HydroChain = {
    showAlert,
    showLoading,
    hideLoading,
    copyToClipboard,
    formatCurrency,
    formatNumber,
    formatDate,
    timeAgo,
    validateForm,
    apiRequest,
    saveToLocalStorage,
    getFromLocalStorage,
    removeFromLocalStorage,
    isValidEthereumAddress,
    isValidEmail,
    debounce,
    throttle
};
