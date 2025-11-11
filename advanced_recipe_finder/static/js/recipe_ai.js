// AI Recipe Generator functionality

document.addEventListener('DOMContentLoaded', function() {
    const recipeForm = document.getElementById('recipeForm');
    const generateBtn = document.getElementById('generateBtn');
    const recipeResults = document.getElementById('recipeResults');
    const saveRecipeBtn = document.getElementById('saveRecipeBtn');
    
    if (recipeForm) {
        // Handle form submission
        recipeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            generateRecipe();
        });
        
        // Handle save recipe button
        if (saveRecipeBtn) {
            saveRecipeBtn.addEventListener('click', saveGeneratedRecipe);
        }
        
        // Initialize ingredient tags input
        initIngredientTags();
        
        // Load previous generations
        loadPreviousGenerations();
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

// Generate recipe
async function generateRecipe() {
    const ingredients = getIngredientsFromTags();
    const cuisine = document.getElementById('cuisine').value;
    const mealType = document.getElementById('mealType').value;
    const dietaryRestrictions = document.getElementById('dietaryRestrictions').value;
    const generateBtn = document.getElementById('generateBtn');
    const recipeResults = document.getElementById('recipeResults');
    
    if (ingredients.length === 0) {
        showToast('Please enter at least one ingredient', 'warning');
        return;
    }
    
    // Show loading state
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('ingredients', ingredients.join(', '));
        formData.append('cuisine', cuisine);
        formData.append('meal_type', mealType);
        formData.append('dietary_restrictions', dietaryRestrictions);
        
        // Send request to server
        const response = await fetch('/ai_recipe_generator', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const html = await response.text();
            
            // Create a temporary div to parse the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // Extract the results section
            const resultsSection = tempDiv.querySelector('#recipeResults');
            if (resultsSection && recipeResults) {
                recipeResults.innerHTML = resultsSection.innerHTML;
                
                // Initialize recipe interactions
                initRecipeInteractions();
                
                // Save to generation history
                saveToGenerationHistory(ingredients, cuisine, mealType, dietaryRestrictions, recipeResults.innerHTML);
                
                // Scroll to results
                recipeResults.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        console.error('Error generating recipe:', error);
        showToast('Error generating recipe. Please try again.', 'danger');
    } finally {
        // Reset button state
        generateBtn.disabled = false;
        generateBtn.innerHTML = 'Generate Recipe';
    }
}

// Initialize recipe interactions
function initRecipeInteractions() {
    // Add click handlers for nutrition toggle
    const nutritionToggle = document.getElementById('nutritionToggle');
    const nutritionInfo = document.getElementById('nutritionInfo');
    
    if (nutritionToggle && nutritionInfo) {
        nutritionToggle.addEventListener('click', function() {
            nutritionInfo.classList.toggle('d-none');
            this.querySelector('i').classList.toggle('fa-chevron-down');
            this.querySelector('i').classList.toggle('fa-chevron-up');
        });
    }
    
    // Add handler for print recipe button
    const printRecipeBtn = document.getElementById('printRecipeBtn');
    if (printRecipeBtn) {
        printRecipeBtn.addEventListener('click', printRecipe);
    }
}

// Save to generation history
function saveToGenerationHistory(ingredients, cuisine, mealType, dietaryRestrictions, recipeHtml) {
    let generationHistory = JSON.parse(localStorage.getItem('recipeGenerationHistory') || '[]');
    
    generationHistory.unshift({
        ingredients: ingredients,
        cuisine: cuisine,
        mealType: mealType,
        dietaryRestrictions: dietaryRestrictions,
        recipe: recipeHtml,
        timestamp: new Date().toISOString()
    });
    
    // Keep only the last 10 generations
    if (generationHistory.length > 10) {
        generationHistory = generationHistory.slice(0, 10);
    }
    
    localStorage.setItem('recipeGenerationHistory', JSON.stringify(generationHistory));
    
    // Reload history
    loadPreviousGenerations();
}

// Load previous generations
function loadPreviousGenerations() {
    const generationHistory = JSON.parse(localStorage.getItem('recipeGenerationHistory') || '[]');
    const historyContainer = document.getElementById('generationHistory');
    
    if (generationHistory.length > 0 && historyContainer) {
        let historyHTML = '<h5>Recent Generations</h5><div class="list-group mb-4">';
        
        generationHistory.forEach((item, index) => {
            const date = new Date(item.timestamp).toLocaleDateString();
            historyHTML += `
                <a href="#" class="list-group-item list-group-item-action generation-history-item" data-index="${index}">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">Recipe from ${date}</h6>
                        <small>${item.ingredients.length} ingredients</small>
                    </div>
                    <p class="mb-1 text-truncate">${item.ingredients.join(', ')}</p>
                    <small class="text-muted">${item.cuisine} • ${item.mealType}</small>
                </a>
            `;
        });
        
        historyHTML += '</div>';
        historyContainer.innerHTML = historyHTML;
        
        // Add event listeners to history items
        document.querySelectorAll('.generation-history-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                loadGenerationFromHistory(parseInt(this.dataset.index));
            });
        });
    } else if (historyContainer) {
        historyContainer.innerHTML = '<p class="text-muted">No previous generations yet.</p>';
    }
}

// Load generation from history
function loadGenerationFromHistory(index) {
    const generationHistory = JSON.parse(localStorage.getItem('recipeGenerationHistory') || '[]');
    const recipeResults = document.getElementById('recipeResults');
    
    if (generationHistory[index] && recipeResults) {
        recipeResults.innerHTML = generationHistory[index].recipe;
        initRecipeInteractions();
        recipeResults.scrollIntoView({ behavior: 'smooth' });
    }
}

// Save generated recipe
async function saveGeneratedRecipe() {
    const recipeElement = document.getElementById('generatedRecipe');
    if (!recipeElement) {
        showToast('No recipe to save', 'warning');
        return;
    }
    
    try {
        // Extract recipe data
        const recipeData = {
            title: document.querySelector('.recipe-title')?.textContent || 'Generated Recipe',
            ingredients: Array.from(document.querySelectorAll('.ingredients-list li')).map(li => li.textContent.trim()),
            instructions: Array.from(document.querySelectorAll('.instructions-list li')).map(li => li.textContent.trim()),
            cooking_time: parseInt(document.querySelector('.cooking-time')?.textContent) || 0,
            difficulty: document.querySelector('.difficulty')?.textContent || 'Medium',
            category: document.querySelector('.recipe-category')?.textContent || 'Main Course',
            nutritional_info: extractNutritionalInfo()
        };
        
        // Send to server
        const response = await fetch('/save_generated_recipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ recipe: recipeData })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showToast('Recipe saved successfully!', 'success');
        } else {
            throw new Error(data.error || 'Error saving recipe');
        }
    } catch (error) {
        console.error('Error saving recipe:', error);
        showToast('Error saving recipe', 'danger');
    }
}

// Extract nutritional info from the generated recipe
function extractNutritionalInfo() {
    const nutritionItems = document.querySelectorAll('.nutrition-item');
    const nutritionalInfo = {};
    
    nutritionItems.forEach(item => {
        const label = item.querySelector('.nutrition-label')?.textContent.toLowerCase().replace(':', '').trim();
        const value = item.querySelector('.nutrition-value')?.textContent;
        
        if (label && value) {
            // Extract numeric value
            const numericValue = parseFloat(value.replace(/[^\d.]/g, ''));
            if (!isNaN(numericValue)) {
                nutritionalInfo[label] = numericValue;
            }
        }
    });
    
    return nutritionalInfo;
}

// Print recipe
function printRecipe() {
    const recipeElement = document.getElementById('generatedRecipe');
    if (!recipeElement) return;
    
    const printWindow = window.open('', '_blank');
    const recipeTitle = document.querySelector('.recipe-title')?.textContent || 'Generated Recipe';
    
    printWindow.document.write(`
        <html>
            <head>
                <title>${recipeTitle}</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    h1 { color: #333; text-align: center; }
                    .recipe-meta { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; }
                    .meta-item { background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px; }
                    .section-title { border-bottom: 2px solid #0d6efd; padding-bottom: 5px; margin-top: 20px; }
                    .ingredients-list, .instructions-list { padding-left: 20px; }
                    .nutrition-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 20px; }
                    .nutrition-item { background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
                    .nutrition-label { font-weight: bold; }
                </style>
            </head>
            <body>
                ${recipeElement.innerHTML}
                <script>
                    window.onload = function() { window.print(); }
                </script>
            </body>
        </html>
    `);
    printWindow.document.close();
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