// Main JavaScript file for common functionality across the application

// DOM Ready function
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initTooltips();
    
    // Initialize modals
    initModals();
    
    // Initialize form validation
    initFormValidation();
    
    // Initialize responsive navigation
    initResponsiveNav();
    
    // Initialize dark mode toggle if exists
    initDarkMode();
});

// Initialize Bootstrap tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize modals
function initModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function () {
            const input = this.querySelector('input[autofocus]');
            if (input) {
                input.focus();
            }
        });
    });
}

// Initialize form validation
function initFormValidation() {
    // Enable Bootstrap form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// Initialize responsive navigation
function initResponsiveNav() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            const target = document.querySelector(this.dataset.bsTarget);
            target.classList.toggle('show');
        });
    }
}

// Initialize dark mode
function initDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        // Check for saved dark mode preference
        const isDarkMode = localStorage.getItem('darkMode') === 'true';
        
        // Apply dark mode if enabled
        if (isDarkMode) {
            document.body.classList.add('dark-mode');
            darkModeToggle.checked = true;
        }
        
        // Toggle dark mode
        darkModeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'true');
            } else {
                document.body.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'false');
            }
        });
    }
}

// Show loading spinner
function showLoading() {
    const loadingEl = document.getElementById('loadingSpinner');
    if (loadingEl) {
        loadingEl.style.display = 'flex';
    }
}

// Hide loading spinner
function hideLoading() {
    const loadingEl = document.getElementById('loadingSpinner');
    if (loadingEl) {
        loadingEl.style.display = 'none';
    }
}

// Show notification toast
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format cooking time
function formatCookingTime(minutes) {
    if (minutes < 60) {
        return `${minutes} min`;
    } else {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }
}

// Format nutritional values
function formatNutritionalValue(value, unit = '') {
    return value ? `${value}${unit}` : 'N/A';
}

// Update both favorite buttons
function updateFavoriteButtons(recipeId, action) {
    const buttons = document.querySelectorAll(`#favorite-btn-${recipeId}, #favorite-btn-bottom-${recipeId}`);
    buttons.forEach(btn => {
        if (action === 'added') {
            btn.classList.add('active');
            btn.innerHTML = `<i class="fas fa-heart me-2"></i><span class="d-inline-flex align-items-center">Remove from Favorites</span>`;
        } else {
            btn.classList.remove('active');
            btn.innerHTML = `<i class="far fa-heart me-2"></i><span class="d-inline-flex align-items-center">Add to Favorites</span>`;
        }
    });
}



