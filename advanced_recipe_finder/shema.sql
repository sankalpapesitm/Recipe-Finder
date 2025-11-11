-- Create the database
CREATE DATABASE IF NOT EXISTS recipefinder101;
USE recipefinder101;

-- Create users table (updated with new fields)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    dietary_preferences TEXT,
    allergies TEXT,
    image_url VARCHAR(255),
    otp_secret VARCHAR(16),
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create recipes table (updated with image_prompt field)
CREATE TABLE IF NOT EXISTS recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL,
    cooking_time INT,
    difficulty ENUM('Easy', 'Medium', 'Hard'),
    category VARCHAR(100),
    image_url VARCHAR(300),
    image_prompt TEXT,
    nutritional_info TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create favorites table
CREATE TABLE IF NOT EXISTS favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    recipe_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE(user_id, recipe_id)
);

-- Create meal_plans table
CREATE TABLE IF NOT EXISTS meal_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_data TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create generated_recipes table
CREATE TABLE IF NOT EXISTS generated_recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    prompt TEXT NOT NULL,
    recipe_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create nutrition_analysis table (NEW)
CREATE TABLE IF NOT EXISTS nutrition_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ingredients TEXT NOT NULL,
    analysis TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create grocery_list table (NEW - renamed from grocery_lists)
CREATE TABLE IF NOT EXISTS grocery_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity VARCHAR(100),
    is_checked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create diet_plans table (NEW)
CREATE TABLE IF NOT EXISTS diet_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_name VARCHAR(255) NOT NULL,
    goal VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create diet_plan_meals table (NEW)
CREATE TABLE IF NOT EXISTS diet_plan_meals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    diet_plan_id INT NOT NULL,
    day INT NOT NULL,
    meal_type VARCHAR(255) NOT NULL,
    recipe_id INT,
    meal_name VARCHAR(255),
    description TEXT,
    ingredients TEXT,
    prep_time VARCHAR(255),
    FOREIGN KEY (diet_plan_id) REFERENCES diet_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
);

-- Create user_allergies table (NEW)
CREATE TABLE IF NOT EXISTS user_allergies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    allergy VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create meal_tracking table (NEW)
CREATE TABLE IF NOT EXISTS meal_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    diet_plan_meal_id INT NOT NULL,
    status ENUM('Completed', 'Skipped') NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (diet_plan_meal_id) REFERENCES diet_plan_meals(id) ON DELETE CASCADE
);

-- Create weight_tracking table (NEW)
CREATE TABLE IF NOT EXISTS weight_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    weight DECIMAL(5, 2) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create notifications table (NEW)
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create recipe_reviews table (NEW - similar to ratings but with different structure)
CREATE TABLE IF NOT EXISTS recipe_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(recipe_id, user_id)
);

-- OLD TABLES (keep these for backward compatibility)
-- Create views table (for tracking recipe views)
CREATE TABLE IF NOT EXISTS views (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    recipe_id INT NOT NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Create ratings table (old version - you might want to migrate data to recipe_reviews)
CREATE TABLE IF NOT EXISTS ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    recipe_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE(user_id, recipe_id)
);

-- Create dietary_plans table (old version)
CREATE TABLE IF NOT EXISTS dietary_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    goal ENUM('Weight Loss', 'Weight Gain', 'Maintenance', 'Muscle Building', 'Other'),
    daily_calories INT,
    protein_ratio DECIMAL(4,2),
    carb_ratio DECIMAL(4,2),
    fat_ratio DECIMAL(4,2),
    dietary_restrictions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create grocery_lists table (old version - different structure)
CREATE TABLE IF NOT EXISTS grocery_lists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    list_name VARCHAR(100) NOT NULL,
    items TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert sample admin user (password: admin123)
INSERT INTO users (username, email, password_hash, is_admin) 
VALUES ('admin', 'admin@recipefinder.com', '$2b$12$Lx4V5QHqQ7W5p5p5p5p5pO5p5p5p5p5p5p5p5p5p5p5p5p5p5p5p', TRUE)
ON DUPLICATE KEY UPDATE username='admin';

-- Insert sample regular user (password: user123)
INSERT INTO users (username, email, password_hash) 
VALUES ('user', 'user@recipefinder.com', '$2b$12$Lx4V5QHqQ7W5p5p5p5p5pO5p5p5p5p5p5p5p5p5p5p5p5p5p5p')
ON DUPLICATE KEY UPDATE username='user';

-- Insert sample recipes
INSERT INTO recipes (title, ingredients, instructions, cooking_time, difficulty, category, nutritional_info, created_by) VALUES
('Spaghetti Carbonara', '["spaghetti", "eggs", "pancetta", "parmesan cheese", "black pepper", "salt"]', '1. Cook spaghetti according to package instructions.\n2. Fry pancetta until crispy.\n3. Beat eggs with grated parmesan.\n4. Combine hot pasta with pancetta, then mix in egg mixture.\n5. Season with black pepper and serve immediately.', 20, 'Medium', 'Main Course', '{"calories": 650, "protein": 25, "carbs": 75, "fat": 25}', 1),
('Chocolate Chip Cookies', '["flour", "butter", "sugar", "eggs", "chocolate chips", "vanilla extract", "baking soda", "salt"]', '1. Preheat oven to 350°F (175°C).\n2. Cream together butter and sugars.\n3. Beat in eggs and vanilla.\n4. Mix in flour, baking soda, and salt.\n5. Stir in chocolate chips.\n6. Drop onto baking sheets and bake for 10-12 minutes.', 30, 'Easy', 'Dessert', '{"calories": 150, "protein": 2, "carbs": 20, "fat": 7}', 1),
('Vegetable Stir Fry', '["broccoli", "carrots", "bell peppers", "soy sauce", "garlic", "ginger", "rice", "tofu"]', '1. Cook rice according to package instructions.\n2. Cut vegetables into bite-sized pieces.\n3. Heat oil in a wok or large pan.\n4. Add garlic and ginger, stir for 30 seconds.\n5. Add vegetables and tofu, stir fry for 5-7 minutes.\n6. Add soy sauce and serve over rice.', 25, 'Easy', 'Main Course', '{"calories": 350, "protein": 15, "carbs": 50, "fat": 10}', 1),
('Greek Salad', '["cucumber", "tomato", "red onion", "feta cheese", "olives", "olive oil", "lemon juice", "oregano"]', '1. Chop cucumber, tomato, and red onion.\n2. Combine in a bowl with olives and feta cheese.\n3. Whisk together olive oil, lemon juice, and oregano.\n4. Pour dressing over salad and toss to combine.\n5. Serve chilled.', 15, 'Easy', 'Salad', '{"calories": 200, "protein": 8, "carbs": 15, "fat": 12}', 1),
('Chicken Curry', '["chicken breast", "curry powder", "coconut milk", "onion", "garlic", "ginger", "tomato paste"]', '1. Cut chicken into cubes.\n2. Heat oil in a pan and sauté onion, garlic, and ginger.\n3. Add chicken and cook until browned.\n4. Stir in curry powder and tomato paste.\n5. Add coconut milk and simmer for 20 minutes.\n6. Serve with rice or naan.', 40, 'Medium', 'Main Course', '{"calories": 500, "protein": 35, "carbs": 25, "fat": 30}', 1);

-- Create indexes for better performance
CREATE INDEX idx_recipes_category ON recipes(category);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_created_at ON recipes(created_at);
CREATE INDEX idx_favorites_user_id ON favorites(user_id);
CREATE INDEX idx_favorites_recipe_id ON favorites(recipe_id);
CREATE INDEX idx_ratings_recipe_id ON ratings(recipe_id);
CREATE INDEX idx_views_recipe_id ON views(recipe_id);
CREATE INDEX idx_recipe_reviews_recipe_id ON recipe_reviews(recipe_id);
CREATE INDEX idx_grocery_list_user_id ON grocery_list(user_id);
CREATE INDEX idx_diet_plans_user_id ON diet_plans(user_id);
CREATE INDEX idx_diet_plan_meals_diet_plan_id ON diet_plan_meals(diet_plan_id);
CREATE INDEX idx_meal_tracking_user_id ON meal_tracking(user_id);
CREATE INDEX idx_weight_tracking_user_id ON weight_tracking(user_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);