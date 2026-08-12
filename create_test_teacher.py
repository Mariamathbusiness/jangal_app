from app import create_app, get_db
from werkzeug.security import generate_password_hash
import uuid

def create_test_teacher():
    app = create_app()
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        
        username = 'prof1'
        password = 'prof123'
        full_name = 'M. Diallo'
        
        # Vérifier s'il existe déjà
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"⚠️ L'enseignant '{username}' existe déjà.")
        else:
            # Créer l'enseignant
            cursor.execute("""
                INSERT INTO users (uuid, school_id, username, password_hash, role, full_name, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                1,  # school_id par défaut
                username,
                generate_password_hash(password),
                'teacher',  # <-- C'est ce rôle qui est important
                full_name,
                'prof@test.com'
            ))
            conn.commit()
            print(f"✅ Enseignant créé avec succès !")
            print(f"👤 Identifiant : {username}")
            print(f"🔑 Mot de passe : {password}")
            print(f"📛 Nom : {full_name}")
            
        conn.close()

if __name__ == '__main__':
    create_test_teacher()