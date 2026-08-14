import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def inspect_users_table():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non trouvé dans .env")
        return

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print("✅ Connexion à la base de données PostgreSQL de Render...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Récupérer la structure de la table users
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print("\n📊 Structure de la table 'users' :")
        print("-" * 60)
        for col in columns:
            print(f"  - {col[0]:20} | {col[1]:15} | Nullable: {col[2]}")
        print("-" * 60)
        
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    inspect_users_table()