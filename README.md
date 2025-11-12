# AI-Powered Recipe Finder & Meal Planner Web Application

This project is a full-stack Flask application that provides an intelligent cooking and meal planning experience using **Gemini AI models** and a MySQL-backed backend. It includes recipe generation, nutrition analysis, image generation, user authentication, 2FA support, admin dashboards, diet planning, grocery lists, chat-based assistance, and more.

---

## 🚀 Features Overview

### ✅ User Module
- User Registration with password encryption
- Login + Session handling
- Two-Factor Authentication (2FA) using OTP (pyotp)
- Profile management (allergies, dietary preferences)
- Favorite recipes
- Recent recipe activity tracking
- Meal plan history save/view/delete
- Nutrition analysis save/view/delete
- Grocery list management
- Weight & meal tracking

---

### ✅ Admin Module
- Admin login
- Manage users (CRUD)
- Manage recipes (CRUD)
- Add images + nutritional info autogeneration via Gemini
- View platform statistics:
  - User growth
  - Recipe creation trends
  - Category-wise distribution
- Review moderation (delete abusive reviews)

---

### ✅ AI Features

#### 🔹 AI Recipe Generator
- Input ingredients, cuisine, meal type, dietary restrictions
- Generates:
  - Recipe name
  - Ingredients list
  - Step-by-step instructions
  - Estimated cook time
  - Suggest variations

#### 🔹 Meal Planner AI
- Generates **multi-day structured JSON meal plan**
- Supports:
  - Allergies
  - Dietary preferences
  - Number of days
- Saved plans stored in database
- View detailed plan per day

#### 🔹 Nutrition Analysis AI
- User pastes ingredients
- AI returns:
  - Calories
  - Macronutrient breakdown
  - Vitamins & minerals
  - Allergy warnings
  - HTML formatted report

#### 🔹 Food Image Generator AI
- Uses Gemini 2.0 Flash-Exp model
- Generates:
  - Professional food photography quality images
- Optional: Overlay your brand logo

---

## 🛠️ Technology Stack

### ✅ Backend
- Python Flask
- MySQL connection pooling
- Sessions & JWT-like behavior

### ✅ Frontend
- HTML
- CSS
- Bootstrap
- Jinja2 templates
- AJAX/Fetch API (for AI responses)

### ✅ AI Integration
- google-generativeai Python Library
- Gemini models:
  - `gemini-flash-latest` (text)
  - `gemini-2.0-flash-exp` (image generation)

### ✅ What the Chat Assistant Can Do
- Suggest recipes based on ingredients
- Provide complete cooking instructions
- Help with substitutions
- Give quick snacks/meal ideas
- Support dieting questions
- Explain nutritional info
- Provide step-by-step guidance in plain text
- Maintains chat history for better personalization
- Works in real-time using AJAX/Fetch API

### ✅ Implementation Highlights
- Powered by `gemini-flash-latest`
- Chat history saved in `chat_history` table
- Cleans AI responses removing markdown (for clean UI)
- Integrated into user dashboard

## 🥗 Diet Plan Module (AI + Manual Features)

This module allows users to create, view, track, and manage custom **diet plans**.  
It is tightly integrated with AI features and user meal tracking.

### ✅ Diet Plan Features
- Create diet plans manually OR via AI auto-generation
- Plans include:
  - plan_name
  - health goal
  - multiple meals
  - daily schedule
  - ingredients & prep time
- Save multiple diet plans per user
- Activate or deactivate specific plans
- Track meal completion/skip
- Track weight progress
- Daily adherence scoring




