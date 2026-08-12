import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'jangal-secret-key-change-in-production'
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'jangal.db')
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Langues supportées
    LANGUAGES = ['fr', 'en', 'ar']
    BABEL_DEFAULT_LOCALE = 'fr'
    BABEL_DEFAULT_TIMEZONE = 'Africa/Dakar'
    
    # Sync
    SYNC_SERVER_URL = os.environ.get('SYNC_SERVER_URL', 'http://localhost:5001')
    SYNC_ENABLED = os.environ.get('SYNC_ENABLED', 'False').lower() == 'true'