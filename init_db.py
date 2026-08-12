from app import create_app, get_db
from werkzeug.security import generate_password_hash
import uuid

def create_initial_admin():
    app = create_app()
    
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        
        # Créer une école par défaut
        cursor.execute("""
            INSERT OR IGNORE INTO schools (uuid, name, address, level_types, grading_config)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            "École Par défaut",
            "Dakar, Sénégal",
            '["preschool", "primary", "secondary", "higher_edu"]',
            '{"max": 20, "passing": 10}'
        ))
        
        school_id = cursor.lastrowid or 1
        
        # Créer un super-admin
        cursor.execute("""
            INSERT OR IGNORE INTO users (uuid, school_id, username, password_hash, role, full_name, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            school_id,
            'admin',
            generate_password_hash('admin123'),
            'super_admin',
            'Administrateur',
            'admin@jangal.app'
        ))
        
        conn.commit()
        conn.close()
        print("✅ Admin initial créé : admin / admin123")

if __name__ == '__main__':
    create_initial_admin()