// Function to create food-themed background
function createFoodBackground() {
    console.log('Creating recipe-themed background...');
    const container = document.querySelector('.recipe-background');
    if (!container) {
        console.error('Background container not found');
        return;
    }

    // Clear existing elements
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    // Food icon types
    const foodIcons = ['vegetables', 'fruits', 'chef', 'pot', 'recipe', 'utensils', 'bread', 'dessert'];
    
    // Create food icons
    const numberOfFoodIcons = 30; // Increased number of food icons
    
    for (let i = 0; i < numberOfFoodIcons; i++) {
        const foodIcon = document.createElement('div');
        const iconType = foodIcons[Math.floor(Math.random() * foodIcons.length)];
        foodIcon.className = `food-icon ${iconType}`;
        
        // Random position
        foodIcon.style.left = `${Math.random() * 100}%`;
        foodIcon.style.top = `${Math.random() * 100}%`;
        
        // Random animation delay and duration
        foodIcon.style.animationDelay = `${Math.random() * 5}s`;
        foodIcon.style.animationDuration = `${5 + Math.random() * 5}s`;
        
        container.appendChild(foodIcon);
    }
    
    // Create a subtle movement effect
    function moveElements() {
        const foodIcons = document.querySelectorAll('.food-icon');
        
        foodIcons.forEach(element => {
            const currentX = parseFloat(element.style.left) || 0;
            const speed = parseFloat(element.dataset.speed) || 0.03;
            
            let newX = currentX + speed;
            if (newX > 100) newX = -5;
            
            element.style.left = `${newX}%`;
        });
        requestAnimationFrame(moveElements);
    }

    // Start the movement animation
    moveElements();
}

// Run on page load
document.addEventListener('DOMContentLoaded', createFoodBackground);

// Run when theme changes
document.addEventListener('themeChanged', createFoodBackground);