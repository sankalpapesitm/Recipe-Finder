import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'recipefinder101'
    MYSQL_CURSORCLASS = 'DictCursor'
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # API Keys - All API keys configured here only
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'AIzaSyBPbyIU5WW-TneqL7AVBUZecVAt-764I74'
    BYTEZ_API_KEY = os.environ.get('BYTEZ_API_KEY') or 'fca34f9c49ef4fb9170d8b1360801ba3'

