import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def init_production_db():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non trouvé.")
        return

    # Render utilise parfois 'postgres://' au lieu de 'postgresql://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print("✅ Connexion à la base de données PostgreSQL de Render...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Chercher le fichier schema.sql (à la racine ou dans le dossier app/)
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            schema_path = os.path.join(os.path.dirname(__file__), 'app', 'schema.sql')
            
        if os.path.exists(schema_path):
            print("📂 Fichier schema.sql trouvé. Création des tables en cours...")
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Exécuter le script SQL
            cursor.execute(schema_sql)
            conn.commit()
            print("🎉 Base de données PostgreSQL initialisée avec succès !")
        else:
            print("⚠️ Fichier schema.sql introuvable. Vérifiez qu'il est bien dans le projet.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation : {e}")

if __name__ == "__main__":
    init_production_db()