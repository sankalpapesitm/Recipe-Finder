// Meal planner functionality - Updated version
document.addEventListener('DOMContentLoaded', function() {
    const mealPlanForm = document.getElementById('mealPlanForm');
    const generatePlanBtn = document.getElementById('generatePlanBtn');
    const mealPlanResults = document.getElementById('mealPlanResults');
    const savePlanBtn = document.getElementById('savePlanBtn');
    
    // Initialize meal item expansion
    document.querySelectorAll('.meal-item').forEach(item => {
        item.addEventListener('click', function() {
            this.classList.toggle('expanded');
        });
    });
    
    // Set default start date to today
    const startDateInput = document.getElementById('startDate');
    if (startDateInput && !startDateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        startDateInput.value = today;
        updateEndDate();
    }
    
    // Update end date when days change
    const daysSelect = document.getElementById('days');
    if (daysSelect) {
        daysSelect.addEventListener('change', updateEndDate);
    }
    
    // Generate grocery list
    const generateGroceryBtn = document.getElementById('generateGroceryBtn');
    if (generateGroceryBtn) {
        generateGroceryBtn.addEventListener('click', generateGroceryList);
    }
    
    // Print plan
    const printPlanBtn = document.getElementById('printPlanBtn');
    if (printPlanBtn) {
        printPlanBtn.addEventListener('click', () => window.print());
    }
    
    if (mealPlanForm) {
        // Handle form submission
        mealPlanForm.addEventListener('submit', function(e) {
            e.preventDefault();
            generateMealPlan();
        });
        
        // Handle save plan button
        if (savePlanBtn) {
            savePlanBtn.addEventListener('click', saveMealPlan);
        }
        
        // Load saved meal plans
        loadSavedMealPlans();
        
        // Initialize date inputs
        initDateInputs();
    }
});

// Initialize date inputs
function initDateInputs() {
    const startDateInput = document.getElementById('startDate');
    const daysInput = document.getElementById('days');
    const endDateSpan = document.getElementById('endDate');
    
    if (startDateInput && daysInput && endDateSpan) {
        // Set default start date to today
        const today = new Date();
        startDateInput.value = today.toISOString().split('T')[0];
        
        // Update end date when start date or days change
        const updateEndDate = function() {
            const startDate = new Date(startDateInput.value);
            const days = parseInt(daysInput.value) || 7;
            const endDate = new Date(startDate);
            endDate.setDate(startDate.getDate() + days - 1);
            
            endDateSpan.textContent = endDate.toLocaleDateString();
        };
        
        startDateInput.addEventListener('change', updateEndDate);
        daysInput.addEventListener('input', updateEndDate);
        
        // Initial update
        updateEndDate();
    }
}

// Update end date based on start date and days
function updateEndDate() {
    const startDateInput = document.getElementById('startDate');
    const daysSelect = document.getElementById('days');
    const endDateElement = document.getElementById('endDate');
    
    if (startDateInput && daysSelect && endDateElement && startDateInput.value) {
        const startDate = new Date(startDateInput.value);
        const days = parseInt(daysSelect.value);
        const endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + days - 1);
        
        endDateElement.textContent = endDate.toISOString().split('T')[0];
    }
}

// Generate meal plan
async function generateMealPlan() {
    const mealPlanForm = document.getElementById('mealPlanForm');
    const generatePlanBtn = document.getElementById('generatePlanBtn');
    const mealPlanResults = document.getElementById('mealPlanResults');
    
    // Show loading state
    generatePlanBtn.disabled = true;
    generatePlanBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    
    try {
        // Create form data
        const formData = new FormData(mealPlanForm);
        
        // Send request to server
        const response = await fetch('/meal_planner', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const html = await response.text();
            
            // Create a temporary div to parse the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // Extract the results section
            const resultsSection = tempDiv.querySelector('#mealPlanResults');
            if (resultsSection && mealPlanResults) {
                mealPlanResults.innerHTML = resultsSection.innerHTML;
                
                // Reinitialize meal item expansion
                document.querySelectorAll('.meal-item').forEach(item => {
                    item.addEventListener('click', function() {
                        this.classList.toggle('expanded');
                    });
                });
                
                // Scroll to results
                mealPlanResults.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        console.error('Error generating meal plan:', error);
        showToast('Error generating meal plan. Please try again.', 'danger');
    } finally {
        // Reset button state
        generatePlanBtn.disabled = false;
        generatePlanBtn.innerHTML = 'Generate Meal Plan';
    }
}

// Generate grocery list from meal plan
function generateGroceryList() {
    const ingredients = new Set();
    
    // Collect all ingredients from the meal plan
    document.querySelectorAll('.ingredients-list li').forEach(li => {
        ingredients.add(li.textContent.trim());
    });
    
    if (ingredients.size === 0) {
        alert('No ingredients found in the meal plan.');
        return;
    }
    
    // Create and display grocery list
    const groceryList = Array.from(ingredients).sort().join('\n• ');
    
    // Show in a modal or alert
    alert('Grocery List:\n\n• ' + groceryList);
    
    // Alternatively, display it in the modal if available
    const groceryListElement = document.getElementById('groceryList');
    if (groceryListElement) {
        groceryListElement.innerHTML = '<ul><li>' + Array.from(ingredients).sort().join('</li><li>') + '</li></ul>';
        
        // Show the modal
        const groceryModal = new bootstrap.Modal(document.getElementById('groceryModal'));
        groceryModal.show();
    }
}

// Print grocery list
function printGroceryList() {
    const groceryListElement = document.getElementById('groceryList');
    if (!groceryListElement) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>Grocery List</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    h1 { color: #333; }
                    ul { list-style-type: none; padding: 0; }
                    li { padding: 5px 0; border-bottom: 1px solid #eee; }
                </style>
            </head>
            <body>
                <h1>Grocery List</h1>
                ${groceryListElement.innerHTML}
                <script>
                    window.onload = function() { window.print(); }
                </script>
            </body>
        </html>
    `);
    printWindow.document.close();
}

// Save meal plan
async function saveMealPlan() {
    const mealPlanData = document.getElementById('mealPlan')?.innerHTML;
    if (!mealPlanData) {
        showToast('No meal plan to save', 'warning');
        return;
    }
    
    try {
        // In a real application, this would send the data to the server
        // For now, we'll save to localStorage
        
        let savedPlans = JSON.parse(localStorage.getItem('savedMealPlans') || '[]');
        
        const planName = prompt('Enter a name for this meal plan:') || 'My Meal Plan';
        
        savedPlans.push({
            name: planName,
            data: mealPlanData,
            date: new Date().toISOString()
        });
        
        localStorage.setItem('savedMealPlans', JSON.stringify(savedPlans));
        
        showToast('Meal plan saved successfully!', 'success');
        
        // Reload saved plans
        loadSavedMealPlans();
    } catch (error) {
        console.error('Error saving meal plan:', error);
        showToast('Error saving meal plan', 'danger');
    }
}

// Load saved meal plans
function loadSavedMealPlans() {
    const savedPlansContainer = document.getElementById('savedPlans');
    if (!savedPlansContainer) return;
    
    const savedPlans = JSON.parse(localStorage.getItem('savedMealPlans') || '[]');
    
    if (savedPlans.length === 0) {
        savedPlansContainer.innerHTML = '<p class="text-muted">No saved meal plans yet.</p>';
        return;
    }
    
    let plansHTML = '<h5>Saved Meal Plans</h5><div class="list-group">';
    
    savedPlans.forEach((plan, index) => {
        const date = new Date(plan.date).toLocaleDateString();
        plansHTML += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${plan.name}</h6>
                    <small>${date}</small>
                </div>
                <div class="btn-group btn-group-sm mt-2">
                    <button class="btn btn-outline-primary view-plan" data-index="${index}">
                        <i class="fas fa-eye me-1"></i> View
                    </button>
                    <button class="btn btn-outline-danger delete-plan" data-index="${index}">
                        <i class="fas fa-trash me-1"></i> Delete
                    </button>
                </div>
            </div>
        `;
    });
    
    plansHTML += '</div>';
    savedPlansContainer.innerHTML = plansHTML;
    
    // Add event listeners
    document.querySelectorAll('.view-plan').forEach(btn => {
        btn.addEventListener('click', function() {
            viewSavedPlan(parseInt(this.dataset.index));
        });
    });
    
    document.querySelectorAll('.delete-plan').forEach(btn => {
        btn.addEventListener('click', function() {
            deleteSavedPlan(parseInt(this.dataset.index));
        });
    });
}

// View saved plan
function viewSavedPlan(index) {
    const savedPlans = JSON.parse(localStorage.getItem('savedMealPlans') || '[]');
    const mealPlanResults = document.getElementById('mealPlanResults');
    
    if (savedPlans[index] && mealPlanResults) {
        mealPlanResults.innerHTML = savedPlans[index].data;
        
        // Reinitialize meal item expansion
        document.querySelectorAll('.meal-item').forEach(item => {
            item.addEventListener('click', function() {
                this.classList.toggle('expanded');
            });
        });
        
        mealPlanResults.scrollIntoView({ behavior: 'smooth' });
    }
}

// Delete saved plan
function deleteSavedPlan(index) {
    if (confirm('Are you sure you want to delete this meal plan?')) {
        let savedPlans = JSON.parse(localStorage.getItem('savedMealPlans') || '[]');
        savedPlans.splice(index, 1);
        localStorage.setItem('savedMealPlans', JSON.stringify(savedPlans));
        
        showToast('Meal plan deleted', 'info');
        loadSavedMealPlans();
    }
}

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1060';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}