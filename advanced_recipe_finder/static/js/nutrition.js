// Nutrition helper functionality

document.addEventListener('DOMContentLoaded', function() {
    const nutritionForm = document.getElementById('nutritionForm');
    const ingredientsInput = document.getElementById('ingredientsInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const nutritionResults = document.getElementById('nutritionResults');
    
    if (nutritionForm) {
        // Handle form submission
        nutritionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            analyzeNutrition();
        });
        
        // Initialize ingredient tags input
        initIngredientTags();
        
        // Load previous analysis if available
        loadPreviousAnalysis();
    }
});

// Initialize ingredient tags input
function initIngredientTags() {
    const ingredientsInput = document.getElementById('ingredientsInput');
    if (!ingredientsInput) return;
    
    // Create tags container
    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'ingredient-tags-container';
    ingredientsInput.parentNode.insertBefore(tagsContainer, ingredientsInput.nextSibling);
    
    // Handle input events
    ingredientsInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && this.value.trim()) {
            e.preventDefault();
            addIngredientTag(this.value.trim());
            this.value = '';
        } else if (e.key === 'Backspace' && this.value === '') {
            // Remove last tag when backspace is pressed on empty input
            const tags = tagsContainer.querySelectorAll('.ingredient-tag');
            if (tags.length > 0) {
                tags[tags.length - 1].remove();
            }
        }
    });
    
    // Handle blur event
    ingredientsInput.addEventListener('blur', function() {
        if (this.value.trim()) {
            addIngredientTag(this.value.trim());
            this.value = '';
        }
    });
}

// Add ingredient tag
function addIngredientTag(ingredient) {
    const tagsContainer = document.querySelector('.ingredient-tags-container');
    if (!tagsContainer) return;
    
    const tag = document.createElement('span');
    tag.className = 'ingredient-tag badge bg-primary me-1 mb-1';
    tag.innerHTML = `
        ${ingredient}
        <button type="button" class="btn-close btn-close-white ms-1" aria-label="Remove"></button>
    `;
    
    // Add remove functionality
    const closeBtn = tag.querySelector('.btn-close');
    closeBtn.addEventListener('click', function() {
        tag.remove();
    });
    
    tagsContainer.appendChild(tag);
}

// Get ingredients from tags
function getIngredientsFromTags() {
    const tags = document.querySelectorAll('.ingredient-tag');
    const ingredients = [];
    
    tags.forEach(tag => {
        // Extract text without the close button text
        const tagText = tag.textContent.trim();
        ingredients.push(tagText);
    });
    
    return ingredients;
}

// Analyze nutrition
async function analyzeNutrition() {
    const ingredients = getIngredientsFromTags();
    const analyzeBtn = document.getElementById('analyzeBtn');
    const nutritionResults = document.getElementById('nutritionResults');
    
    if (ingredients.length === 0) {
        showToast('Please enter at least one ingredient', 'warning');
        return;
    }
    
    // Show loading state
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...';
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('ingredients', ingredients.join(', '));
        
        // Send request to server
        const response = await fetch('/nutrition_helper', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const html = await response.text();
            
            // Create a temporary div to parse the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // Extract the results section
            const resultsSection = tempDiv.querySelector('#nutritionResults');
            if (resultsSection && nutritionResults) {
                nutritionResults.innerHTML = resultsSection.innerHTML;
                
                // Save analysis to history
                saveToAnalysisHistory(ingredients, nutritionResults.innerHTML);
                
                // Scroll to results
                nutritionResults.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        console.error('Error analyzing nutrition:', error);
        showToast('Error analyzing ingredients. Please try again.', 'danger');
    } finally {
        // Reset button state
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'Analyze Nutrition';
    }
}

// Save analysis to history
function saveToAnalysisHistory(ingredients, analysisHtml) {
    let analysisHistory = JSON.parse(localStorage.getItem('nutritionAnalysisHistory') || '[]');
    
    analysisHistory.unshift({
        ingredients: ingredients,
        analysis: analysisHtml,
        timestamp: new Date().toISOString()
    });
    
    // Keep only the last 10 analyses
    if (analysisHistory.length > 10) {
        analysisHistory = analysisHistory.slice(0, 10);
    }
    
    localStorage.setItem('nutritionAnalysisHistory', JSON.stringify(analysisHistory));
}

// Load previous analysis
function loadPreviousAnalysis() {
    const analysisHistory = JSON.parse(localStorage.getItem('nutritionAnalysisHistory') || '[]');
    const historyContainer = document.getElementById('analysisHistory');
    
    if (analysisHistory.length > 0 && historyContainer) {
        let historyHTML = '<h5>Recent Analyses</h5><div class="list-group mb-4">';
        
        analysisHistory.forEach((item, index) => {
            const date = new Date(item.timestamp).toLocaleDateString();
            historyHTML += `
                <a href="#" class="list-group-item list-group-item-action analysis-history-item" data-index="${index}">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">Analysis from ${date}</h6>
                        <small>${item.ingredients.length} ingredients</small>
                    </div>
                    <p class="mb-1 text-truncate">${item.ingredients.join(', ')}</p>
                </a>
            `;
        });
        
        historyHTML += '</div>';
        historyContainer.innerHTML = historyHTML;
        
        // Add event listeners to history items
        document.querySelectorAll('.analysis-history-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                loadAnalysisFromHistory(parseInt(this.dataset.index));
            });
        });
    }
}

// Load analysis from history
function loadAnalysisFromHistory(index) {
    const analysisHistory = JSON.parse(localStorage.getItem('nutritionAnalysisHistory') || '[]');
    const nutritionResults = document.getElementById('nutritionResults');
    
    if (analysisHistory[index] && nutritionResults) {
        nutritionResults.innerHTML = analysisHistory[index].analysis;
        nutritionResults.scrollIntoView({ behavior: 'smooth' });
    }
}

// Initialize sample ingredients
function initSampleIngredients() {
    const sampleIngredients = document.querySelectorAll('.sample-ingredient');
    sampleIngredients.forEach(ingredient => {
        ingredient.addEventListener('click', function() {
            addIngredientTag(this.textContent.trim());
        });
    });
}

// Initialize sample ingredients
initSampleIngredients();