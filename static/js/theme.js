// HydroChain Theme Management

// Theme Configuration
const THEMES = {
    DARK: 'dark',
    LIGHT: 'light'
};

const THEME_STORAGE_KEY = 'hydrochain-theme';
const THEME_TRANSITION_DURATION = 300; // milliseconds

// Theme State
let currentTheme = THEMES.DARK;
let isTransitioning = false;

// Initialize Theme System
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    setupThemeToggle();
});

function initializeTheme() {
    // Get saved theme from localStorage or default to dark
    currentTheme = getSavedTheme() || THEMES.DARK;
    
    // Apply theme immediately to prevent flash
    applyTheme(currentTheme, false);
    
    // Update toggle button state
    updateThemeToggleIcon();
}

function getSavedTheme() {
    try {
        return localStorage.getItem(THEME_STORAGE_KEY);
    } catch (error) {
        console.warn('Could not access localStorage for theme:', error);
        return null;
    }
}

function saveTheme(theme) {
    try {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (error) {
        console.warn('Could not save theme to localStorage:', error);
    }
}

function setupThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        
        // Add keyboard support
        themeToggle.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggleTheme();
            }
        });
    }
}

function toggleTheme() {
    if (isTransitioning) return;
    
    const newTheme = currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
    setTheme(newTheme);
}

function setTheme(theme, withTransition = true) {
    if (theme === currentTheme || isTransitioning) return;
    
    if (withTransition) {
        isTransitioning = true;
        addTransitionClass();
    }
    
    currentTheme = theme;
    applyTheme(theme, withTransition);
    updateThemeToggleIcon();
    saveTheme(theme);
    
    // Dispatch custom event
    document.dispatchEvent(new CustomEvent('themeChanged', {
        detail: { theme: theme }
    }));
    
    if (withTransition) {
        setTimeout(() => {
            removeTransitionClass();
            isTransitioning = false;
        }, THEME_TRANSITION_DURATION);
    }
}

function applyTheme(theme, withTransition = true) {
    const htmlElement = document.documentElement;
    
    // Set data attribute for CSS
    htmlElement.setAttribute('data-theme', theme);
    
    // Update body class for legacy support
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add(`theme-${theme}`);
    
    // Update meta theme-color for mobile browsers
    updateMetaThemeColor(theme);
    
    // Apply theme-specific styles
    applyThemeSpecificStyles(theme);
    
    if (withTransition) {
        // Announce theme change for accessibility
        announceThemeChange(theme);
    }
}

function addTransitionClass() {
    document.body.classList.add('theme-transitioning');
    
    // Add transition styles
    const style = document.createElement('style');
    style.id = 'theme-transition-styles';
    style.textContent = `
        .theme-transitioning * {
            transition: background-color ${THEME_TRANSITION_DURATION}ms ease,
                       color ${THEME_TRANSITION_DURATION}ms ease,
                       border-color ${THEME_TRANSITION_DURATION}ms ease,
                       box-shadow ${THEME_TRANSITION_DURATION}ms ease !important;
        }
    `;
    document.head.appendChild(style);
}

function removeTransitionClass() {
    document.body.classList.remove('theme-transitioning');
    
    // Remove transition styles
    const transitionStyles = document.getElementById('theme-transition-styles');
    if (transitionStyles) {
        transitionStyles.remove();
    }
}

function updateThemeToggleIcon() {
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        if (currentTheme === THEMES.DARK) {
            themeIcon.className = 'fas fa-sun';
            themeIcon.parentElement.setAttribute('title', 'Switch to light mode');
        } else {
            themeIcon.className = 'fas fa-moon';
            themeIcon.parentElement.setAttribute('title', 'Switch to dark mode');
        }
    }
}

function updateMetaThemeColor(theme) {
    let themeColorMeta = document.querySelector('meta[name="theme-color"]');
    
    if (!themeColorMeta) {
        themeColorMeta = document.createElement('meta');
        themeColorMeta.name = 'theme-color';
        document.head.appendChild(themeColorMeta);
    }
    
    const themeColors = {
        [THEMES.DARK]: '#0a0a0a',
        [THEMES.LIGHT]: '#ffffff'
    };
    
    themeColorMeta.content = themeColors[theme];
}

function applyThemeSpecificStyles(theme) {
    // Update CSS custom properties dynamically if needed
    const root = document.documentElement;
    
    if (theme === THEMES.LIGHT) {
        // Light theme specific adjustments
        root.style.setProperty('--shadow-sm', '0 2px 4px rgba(0, 0, 0, 0.1)');
        root.style.setProperty('--shadow-md', '0 4px 8px rgba(0, 0, 0, 0.15)');
        root.style.setProperty('--shadow-lg', '0 8px 16px rgba(0, 0, 0, 0.2)');
    } else {
        // Dark theme specific adjustments
        root.style.setProperty('--shadow-sm', '0 2px 4px rgba(0, 0, 0, 0.3)');
        root.style.setProperty('--shadow-md', '0 4px 8px rgba(0, 0, 0, 0.4)');
        root.style.setProperty('--shadow-lg', '0 8px 16px rgba(0, 0, 0, 0.5)');
    }
}

function announceThemeChange(theme) {
    // Create announcement for screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = `Switched to ${theme} theme`;
    
    document.body.appendChild(announcement);
    
    // Remove announcement after it's been read
    setTimeout(() => {
        if (announcement.parentNode) {
            announcement.remove();
        }
    }, 1000);
}

// Auto Theme Detection
function detectSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return THEMES.DARK;
    }
    return THEMES.LIGHT;
}

function setupSystemThemeDetection() {
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        mediaQuery.addEventListener('change', function(e) {
            // Only auto-switch if user hasn't manually set a preference
            if (!getSavedTheme()) {
                const systemTheme = e.matches ? THEMES.DARK : THEMES.LIGHT;
                setTheme(systemTheme);
            }
        });
    }
}

// Theme Utilities
function getCurrentTheme() {
    return currentTheme;
}

function isDarkTheme() {
    return currentTheme === THEMES.DARK;
}

function isLightTheme() {
    return currentTheme === THEMES.LIGHT;
}

// High Contrast Mode Support
function setupHighContrastDetection() {
    if (window.matchMedia) {
        const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
        
        const applyHighContrast = (matches) => {
            document.body.classList.toggle('high-contrast', matches);
        };
        
        // Apply initial state
        applyHighContrast(highContrastQuery.matches);
        
        // Listen for changes
        highContrastQuery.addEventListener('change', (e) => {
            applyHighContrast(e.matches);
        });
    }
}

// Reduced Motion Support
function setupReducedMotionDetection() {
    if (window.matchMedia) {
        const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        const applyReducedMotion = (matches) => {
            document.body.classList.toggle('reduced-motion', matches);
            
            if (matches) {
                // Disable transitions and animations
                const style = document.createElement('style');
                style.id = 'reduced-motion-styles';
                style.textContent = `
                    .reduced-motion *,
                    .reduced-motion *::before,
                    .reduced-motion *::after {
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                        scroll-behavior: auto !important;
                    }
                `;
                document.head.appendChild(style);
            } else {
                const reducedMotionStyles = document.getElementById('reduced-motion-styles');
                if (reducedMotionStyles) {
                    reducedMotionStyles.remove();
                }
            }
        };
        
        // Apply initial state
        applyReducedMotion(reducedMotionQuery.matches);
        
        // Listen for changes
        reducedMotionQuery.addEventListener('change', (e) => {
            applyReducedMotion(e.matches);
        });
    }
}

// Initialize accessibility features
document.addEventListener('DOMContentLoaded', function() {
    setupSystemThemeDetection();
    setupHighContrastDetection();
    setupReducedMotionDetection();
});

// Export functions for global use
window.HydroChainTheme = {
    toggle: toggleTheme,
    set: setTheme,
    get: getCurrentTheme,
    isDark: isDarkTheme,
    isLight: isLightTheme,
    detectSystem: detectSystemTheme,
    themes: THEMES
};

// Add to main HydroChain namespace if it exists
if (window.HydroChain) {
    window.HydroChain.theme = window.HydroChainTheme;
}
