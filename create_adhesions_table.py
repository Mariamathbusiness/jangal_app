import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_adhesions_table():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL manquant. Ajoutez-le temporairement dans votre .env")
        return
    
    # Correction du format d'URL pour psycopg2
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    print("✅ Connexion à la base de données Render...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("🔧 Création de la table 'adhesions' en cours...")
        
        # Création de la table avec toutes les colonnes nécessaires
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adhesions (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                school_name TEXT,
                school_type TEXT,
                student_count TEXT,
                address TEXT,
                creation_year TEXT,
                contact_name TEXT,
                contact_role TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                current_system TEXT,
                challenges TEXT,
                features_interest TEXT,
                start_timeline TEXT,
                has_computer TEXT,
                message TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("🎉 Succès ! La table 'adhesions' a été créée avec succès.")
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    create_adhesions_table()