// Animation system using Framer Motion
class AnimationManager {
    constructor() {
        this.init();
    }

    init() {
        // Add motion div around main content
        this.wrapMainContent();
        
        // Initialize page transitions
        this.initializePageTransitions();
        
        // Setup intersection observer for reveal animations
        this.setupRevealAnimations();
    }

    wrapMainContent() {
        const main = document.querySelector('main');
        if (!main || main.querySelector('.motion-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'motion-wrapper';
        
        // Move main's content into wrapper
        while (main.firstChild) {
            wrapper.appendChild(main.firstChild);
        }
        main.appendChild(wrapper);

        // Ensure content is visible immediately
        wrapper.style.opacity = '1';
        wrapper.style.transform = 'none';
    }

    initializePageTransitions() {
        window.addEventListener('beforeunload', () => {
            const wrapper = document.querySelector('.motion-wrapper');
            if (wrapper) {
                window.motion.animate(wrapper, {
                    opacity: 0,
                    y: -20
                }, {
                    duration: 0.3,
                    ease: [0.22, 1, 0.36, 1]
                });
            }
        });
    }

    setupRevealAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateElement(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });

        // Observe elements with reveal classes
        document.querySelectorAll('.reveal-on-scroll').forEach(el => {
            observer.observe(el);
        });
    }

    animateElement(element) {
        const delay = element.dataset.delay || 0;
        const animation = element.dataset.animation || 'fadeIn';

        const animations = {
            fadeIn: {
                opacity: [0, 1],
                y: [20, 0]
            },
            slideIn: {
                x: [-50, 0],
                opacity: [0, 1]
            },
            scaleIn: {
                scale: [0.9, 1],
                opacity: [0, 1]
            }
        };

        window.motion.animate(element, animations[animation], {
            duration: 0.6,
            delay: parseFloat(delay),
            ease: [0.22, 1, 0.36, 1]
        });
    }

    // Utility method for custom animations
    static animate(element, animation) {
        if (!element || !animation) return;

        window.motion.animate(element, animation.properties, {
            duration: animation.duration || 0.3,
            ease: animation.ease || [0.22, 1, 0.36, 1],
            delay: animation.delay || 0
        });
    }
}

// Initialize animation manager
document.addEventListener('DOMContentLoaded', () => {
    window.animationManager = new AnimationManager();
});