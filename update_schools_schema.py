import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def update_schools_schema():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non trouvé dans votre fichier .env")
        return

    # Correction du format d'URL pour psycopg2
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print("✅ Connexion à la base de données PostgreSQL de Render...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Mise à jour de la table 'schools' en cours...")
        
        # Ajout des colonnes manquantes (IF NOT EXISTS évite les erreurs si elles sont déjà là)
        cursor.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS director_name TEXT;")
        cursor.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS start_date DATE;")
        cursor.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS end_date DATE;")
        cursor.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';")
        
        conn.commit()
        print("🎉 Schéma de la table 'schools' mis à jour avec succès !")
        print("   -> director_name (TEXT)")
        print("   -> start_date (DATE)")
        print("   -> end_date (DATE)")
        print("   -> status (TEXT)")
        
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour : {e}")

if __name__ == "__main__":
    update_schools_schema()