import os
import uuid
import psycopg2
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def create_admin():
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
        
        # Vérifier si l'utilisateur admin existe déjà
        cursor.execute("SELECT id FROM users WHERE username = %s", ("admin",))
        if cursor.fetchone():
            print("⚠️ Un utilisateur admin existe déjà.")
        else:
            # Créer un utilisateur admin avec les bons noms de colonnes
            admin_uuid = str(uuid.uuid4())
            password_hash = generate_password_hash("admin123")
            
            cursor.execute("""
                INSERT INTO users (uuid, username, password_hash, role, full_name, email, is_active, school_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (admin_uuid, "admin", password_hash, "admin", "Administrateur Jangal", "admin@jangal.sn", 1, 1))
            
            conn.commit()
            print("🎉 Utilisateur admin créé avec succès !")
            print("📧 Email : admin@jangal.sn")
            print("🔑 Mot de passe : admin123")
            print("👤 Username : admin")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    create_admin()