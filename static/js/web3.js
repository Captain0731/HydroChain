// HydroChain Web3 Integration

// Web3 Configuration
const SUPPORTED_NETWORKS = {
    1: 'Ethereum Mainnet',
    3: 'Ropsten Testnet',
    4: 'Rinkeby Testnet',
    5: 'Goerli Testnet',
    42: 'Kovan Testnet',
    137: 'Polygon Mainnet',
    80001: 'Polygon Mumbai Testnet'
};

const PREFERRED_NETWORK_ID = 1; // Ethereum Mainnet

// Global Web3 Variables
let web3;
let currentAccount = null;
let currentNetwork = null;
let isConnecting = false;

// Initialize Web3
async function initWeb3() {
    if (typeof window.ethereum !== 'undefined') {
        web3 = new Web3(window.ethereum);
        
        // Setup event listeners
        setupWeb3EventListeners();
        
        // Check if already connected
        await checkExistingConnection();
        
        return true;
    } else {
        console.warn('MetaMask not detected');
        return false;
    }
}

function setupWeb3EventListeners() {
    if (window.ethereum) {
        // Account changed
        window.ethereum.on('accountsChanged', handleAccountsChanged);
        
        // Network changed
        window.ethereum.on('chainChanged', handleChainChanged);
        
        // Connection status
        window.ethereum.on('connect', handleConnect);
        window.ethereum.on('disconnect', handleDisconnect);
    }
}

async function checkExistingConnection() {
    try {
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
            currentAccount = accounts[0];
            currentNetwork = await getCurrentNetwork();
            updateWalletUI(currentAccount, currentNetwork);
            return true;
        }
    } catch (error) {
        console.error('Error checking existing connection:', error);
    }
    return false;
}

// Connect Wallet
async function connectWallet() {
    if (isConnecting) {
        return { success: false, message: 'Connection already in progress' };
    }
    
    if (typeof window.ethereum === 'undefined') {
        showMetaMaskInstallPrompt();
        return { success: false, message: 'MetaMask not installed' };
    }
    
    isConnecting = true;
    
    try {
        // Request account access
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });
        
        if (accounts.length === 0) {
            throw new Error('No accounts returned from MetaMask');
        }
        
        currentAccount = accounts[0];
        currentNetwork = await getCurrentNetwork();
        
        // Validate network
        if (!SUPPORTED_NETWORKS[currentNetwork]) {
            showAlert('Unsupported Network', 
                     'Please switch to a supported network (Ethereum, Polygon)', 
                     'warning');
        }
        
        // Update UI
        updateWalletUI(currentAccount, currentNetwork);
        
        // Send to backend
        const result = await registerWalletWithBackend(currentAccount);
        
        if (result.success) {
            showAlert('Success', 'Wallet connected successfully!', 'success');
            return { success: true, account: currentAccount, user: result.user };
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        console.error('Error connecting wallet:', error);
        
        let errorMessage = 'Failed to connect wallet';
        if (error.code === 4001) {
            errorMessage = 'Connection request was rejected';
        } else if (error.code === -32002) {
            errorMessage = 'MetaMask is already processing a request. Please check MetaMask.';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showAlert('Connection Failed', errorMessage, 'error');
        return { success: false, message: errorMessage };
        
    } finally {
        isConnecting = false;
    }
}

async function registerWalletWithBackend(walletAddress) {
    try {
        const response = await fetch('/api/connect-wallet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet_address: walletAddress,
                username: await generateUsername(walletAddress)
            })
        });
        
        const result = await response.json();
        return result;
        
    } catch (error) {
        console.error('Error registering wallet with backend:', error);
        return { success: false, message: 'Backend registration failed' };
    }
}

async function generateUsername(walletAddress) {
    // Generate a simple username based on wallet address
    const suffix = walletAddress.slice(-6);
    return `User${suffix}`;
}

// Disconnect Wallet
async function disconnectWallet() {
    currentAccount = null;
    currentNetwork = null;
    
    // Clear UI
    updateWalletUI(null, null);
    
    // Clear session (redirect to logout)
    window.location.href = '/logout';
}

// Network Functions
async function getCurrentNetwork() {
    try {
        const networkId = await window.ethereum.request({ method: 'net_version' });
        return parseInt(networkId);
    } catch (error) {
        console.error('Error getting network:', error);
        return null;
    }
}

async function switchNetwork(networkId) {
    try {
        await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: `0x${networkId.toString(16)}` }],
        });
        return true;
    } catch (error) {
        console.error('Error switching network:', error);
        
        if (error.code === 4902) {
            // Network not added to MetaMask
            showAlert('Network Not Added', 
                     'This network is not added to your MetaMask. Please add it manually.', 
                     'warning');
        }
        
        return false;
    }
}

// Event Handlers
function handleAccountsChanged(accounts) {
    if (accounts.length === 0) {
        // User disconnected wallet
        handleDisconnect();
    } else if (accounts[0] !== currentAccount) {
        // User switched accounts
        currentAccount = accounts[0];
        updateWalletUI(currentAccount, currentNetwork);
        
        // Reload page to update user context
        showAlert('Account Changed', 'Account switched. Refreshing page...', 'info');
        setTimeout(() => window.location.reload(), 2000);
    }
}

function handleChainChanged(chainId) {
    const networkId = parseInt(chainId, 16);
    currentNetwork = networkId;
    
    updateWalletUI(currentAccount, networkId);
    
    if (!SUPPORTED_NETWORKS[networkId]) {
        showAlert('Unsupported Network', 
                 'You switched to an unsupported network. Please switch to Ethereum or Polygon.', 
                 'warning');
    } else {
        showAlert('Network Changed', 
                 `Switched to ${SUPPORTED_NETWORKS[networkId]}`, 
                 'info', 3000);
    }
}

function handleConnect(connectInfo) {
    console.log('Wallet connected:', connectInfo);
}

function handleDisconnect(error) {
    console.log('Wallet disconnected:', error);
    currentAccount = null;
    currentNetwork = null;
    updateWalletUI(null, null);
}

// UI Updates
function updateWalletUI(account, networkId) {
    // Update wallet status in navbar
    const walletStatus = document.getElementById('walletStatus');
    const walletAddress = document.getElementById('walletAddress');
    const connectBtn = document.getElementById('connectWalletBtn');
    
    if (account) {
        if (walletStatus) {
            walletStatus.style.display = 'block';
        }
        if (walletAddress) {
            walletAddress.textContent = `${account.substring(0, 6)}...${account.substring(38)}`;
        }
        if (connectBtn) {
            connectBtn.style.display = 'none';
        }
        
        // Add network indicator
        updateNetworkIndicator(networkId);
        
    } else {
        if (walletStatus) {
            walletStatus.style.display = 'none';
        }
        if (connectBtn) {
            connectBtn.style.display = 'block';
        }
        
        removeNetworkIndicator();
    }
}

function updateNetworkIndicator(networkId) {
    let indicator = document.getElementById('networkIndicator');
    
    if (!indicator) {
        indicator = document.createElement('span');
        indicator.id = 'networkIndicator';
        indicator.className = 'badge bg-secondary ms-2';
        
        const walletStatus = document.getElementById('walletStatus');
        if (walletStatus) {
            walletStatus.appendChild(indicator);
        }
    }
    
    if (SUPPORTED_NETWORKS[networkId]) {
        indicator.textContent = SUPPORTED_NETWORKS[networkId];
        indicator.className = 'badge bg-success ms-2';
    } else {
        indicator.textContent = 'Unsupported';
        indicator.className = 'badge bg-warning ms-2';
    }
}

function removeNetworkIndicator() {
    const indicator = document.getElementById('networkIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// MetaMask Installation Prompt
function showMetaMaskInstallPrompt() {
    const modalHTML = `
        <div class="modal fade" id="metamaskInstallModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content bg-dark-custom border-0">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-light">
                            <i class="fab fa-ethereum text-primary me-2"></i>
                            MetaMask Required
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center">
                            <img src="https://cdn.jsdelivr.net/gh/MetaMask/brand-resources@master/SVG/metamask-fox.svg" 
                                 alt="MetaMask" width="80" height="80" class="mb-3">
                            <h6 class="text-light mb-3">MetaMask Wallet Required</h6>
                            <p class="text-muted mb-4">
                                To use HydroChain, you need to install the MetaMask browser extension. 
                                MetaMask is a secure wallet that allows you to interact with blockchain applications.
                            </p>
                            <a href="https://metamask.io/download/" target="_blank" rel="noopener" 
                               class="btn btn-primary btn-lg">
                                <i class="fas fa-download me-2"></i>
                                Install MetaMask
                            </a>
                        </div>
                        <div class="mt-4">
                            <h6 class="text-light">After installation:</h6>
                            <ol class="text-muted small">
                                <li>Refresh this page</li>
                                <li>Click "Connect Wallet"</li>
                                <li>Follow MetaMask prompts to connect</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if present
    const existingModal = document.getElementById('metamaskInstallModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('metamaskInstallModal'));
    modal.show();
}

// Utility Functions
function isValidEthereumAddress(address) {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
}

async function getBalance(address = currentAccount) {
    if (!web3 || !address) return null;
    
    try {
        const balance = await web3.eth.getBalance(address);
        return web3.utils.fromWei(balance, 'ether');
    } catch (error) {
        console.error('Error getting balance:', error);
        return null;
    }
}

async function getGasPrice() {
    if (!web3) return null;
    
    try {
        const gasPrice = await web3.eth.getGasPrice();
        return gasPrice;
    } catch (error) {
        console.error('Error getting gas price:', error);
        return null;
    }
}

// Transaction Functions (for future use)
async function sendTransaction(to, value, data = '0x') {
    if (!web3 || !currentAccount) {
        throw new Error('Wallet not connected');
    }
    
    try {
        const gasPrice = await getGasPrice();
        const gasEstimate = await web3.eth.estimateGas({
            from: currentAccount,
            to: to,
            value: value,
            data: data
        });
        
        const transaction = {
            from: currentAccount,
            to: to,
            value: value,
            gas: gasEstimate,
            gasPrice: gasPrice,
            data: data
        };
        
        const txHash = await web3.eth.sendTransaction(transaction);
        return txHash;
        
    } catch (error) {
        console.error('Error sending transaction:', error);
        throw error;
    }
}

// Initialize Web3 when script loads
document.addEventListener('DOMContentLoaded', function() {
    initWeb3();
});

// Export functions for global use
window.connectWallet = connectWallet;
window.disconnectWallet = disconnectWallet;
window.getCurrentNetwork = getCurrentNetwork;
window.switchNetwork = switchNetwork;
window.getBalance = getBalance;
window.isValidEthereumAddress = isValidEthereumAddress;

// Add to HydroChain namespace
if (window.HydroChain) {
    window.HydroChain.web3 = {
        connect: connectWallet,
        disconnect: disconnectWallet,
        getCurrentNetwork,
        switchNetwork,
        getBalance,
        isValidAddress: isValidEthereumAddress,
        currentAccount: () => currentAccount,
        currentNetwork: () => currentNetwork,
        isConnected: () => !!currentAccount
    };
}
