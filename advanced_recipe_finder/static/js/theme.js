// Theme management
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        // Add theme toggle button to navbar
        this.createThemeToggle();
        
        // Apply saved theme
        this.applyTheme(this.theme);
        
        // Listen for OS theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            this.theme = e.matches ? 'dark' : 'light';
            this.applyTheme(this.theme);
        });
    }

    createThemeToggle() {
        const navbarNav = document.querySelector('.navbar-nav:last-child');
        if (!navbarNav) return;

        const themeToggle = document.createElement('li');
        themeToggle.className = 'nav-item';
        themeToggle.innerHTML = `
            <button class="nav-link btn btn-link" id="themeToggle">
                <i class="fas fa-sun"></i>
            </button>
        `;
        
        navbarNav.insertBefore(themeToggle, navbarNav.firstChild);
        
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        this.updateToggleIcon();
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
        localStorage.setItem('theme', this.theme);
    }

    applyTheme(theme) {
        // Ensure content remains visible during theme change
        document.documentElement.style.visibility = 'visible';
        document.documentElement.setAttribute('data-theme', theme);
        this.updateToggleIcon();
    }

    updateToggleIcon() {
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            icon.className = this.theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }
}

// Initialize theme manager
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});