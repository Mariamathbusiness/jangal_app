import os
import sqlite3
import json
from flask import Flask, redirect, url_for, request, session, current_app
from flask_login import LoginManager, current_user
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from config import Config
from dotenv import load_dotenv

# Charger les variables d'environnement (très important pour le .env)
load_dotenv()

# Import conditionnel de PostgreSQL pour éviter les erreurs en local si non installé
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

login_manager = LoginManager()
babel = Babel()
csrf = CSRFProtect()

def get_locale():
    lang = session.get('lang')
    if lang:
        return lang
    return request.accept_languages.best_match(['fr', 'en', 'ar']) or 'fr'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialiser les extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    babel.init_app(app, locale_selector=get_locale)
    csrf.init_app(app)
    
    # Créer les dossiers d'upload
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'imports'), exist_ok=True)
    
    # Initialiser la base de données (intelligent : SQLite ou PostgreSQL)
    init_db(app)
    
    # Import des blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.pedagogical.routes import pedagogical_bp
    from app.financial.routes import financial_bp
    from app.parent_portal.routes import parent_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(pedagogical_bp, url_prefix='/pedagogical')
    app.register_blueprint(financial_bp, url_prefix='/financial')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'parent':
                return redirect(url_for('parent.dashboard'))
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.login'))
        
    # Filtre Jinja pour convertir JSON en liste
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value)
        except:
            return []
    
    return app

def init_db(app):
    # 1. Vérifier si on est en mode Production (Render.com)
    if os.getenv('DATABASE_URL'):
        print("✅ Mode Production détecté : Connexion à la base de données distante (PostgreSQL).")
        return  # On ne crée pas de fichier local sur le serveur cloud

    # 2. Sinon, on initialise SQLite en local (Mode Hors Ligne)
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)
        
        conn.commit()
        conn.close()
        print(f"✅ Base de données SQLite initialisée en local : {db_path}")

def get_db():
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and HAS_PSYCOPG2:
        # --- MODE PRODUCTION (Render.com / PostgreSQL) ---
        # Render utilise parfois 'postgres://' au lieu de 'postgresql://', on corrige ça
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # RealDictCursor permet d'utiliser row['nom_colonne'] exactement comme sqlite3.Row
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return conn
    else:
        # --- MODE LOCAL / HORS LIGNE (SQLite) ---
        db_path = current_app.config['DATABASE']
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn
        def execute_query(query, params=()):
    """Exécute une requête SQL compatible avec SQLite et PostgreSQL"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Si on utilise PostgreSQL, remplacer ? par %s
    if os.getenv('DATABASE_URL'):
        query = query.replace('?', '%s')
    
    cursor.execute(query, params)
    return cursor, conn