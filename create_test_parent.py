from app import create_app, get_db
from werkzeug.security import generate_password_hash
import uuid
import json

def create_test_parent():
    app = create_app()
    
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. Créer l'utilisateur parent
        parent_username = 'parent1'
        parent_password = 'parent123'
        
        # Vérifier si le parent existe déjà
        cursor.execute("SELECT id FROM users WHERE username = ?", (parent_username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"⚠️  L'utilisateur '{parent_username}' existe déjà avec l'ID {existing_user['id']}")
            parent_user_id = existing_user['id']
        else:
            # Créer le nouvel utilisateur
            cursor.execute("""
                INSERT INTO users (uuid, school_id, username, password_hash, role, full_name, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                1,  # school_id par défaut
                parent_username,
                generate_password_hash(parent_password),
                'parent',
                'Parent de Test',
                'parent@test.com'
            ))
            parent_user_id = cursor.lastrowid
            print(f"✅ Utilisateur parent créé : {parent_username} / {parent_password} (ID: {parent_user_id})")
        
        # 2. Trouver un élève existant pour le test
        cursor.execute("SELECT id, first_name, last_name, matricule FROM students LIMIT 1")
        student = cursor.fetchone()
        
        if not student:
            print("❌ Aucun élève trouvé dans la base de données. Veuillez d'abord créer un élève.")
            conn.close()
            return
        
        student_id = student['id']
        student_name = f"{student['last_name']} {student['first_name']}"
        print(f"📚 Élève trouvé pour le test : {student_name} (Matricule: {student['matricule']}, ID: {student_id})")
        
        # 3. Créer le lien parent-élève dans la table parents
        cursor.execute("SELECT id FROM parents WHERE user_id = ?", (parent_user_id,))
        existing_parent = cursor.fetchone()
        
        if existing_parent:
            print(f"⚠️  Le parent existe déjà dans la table parents (ID: {existing_parent['id']}). Mise à jour du lien...")
            cursor.execute("""
                UPDATE parents SET student_ids = ? WHERE user_id = ?
            """, (json.dumps([student_id]), parent_user_id))
        else:
            cursor.execute("""
                INSERT INTO parents (uuid, user_id, student_ids, relationship)
                VALUES (?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                parent_user_id,
                json.dumps([student_id]),
                'père'  # ou 'mère', 'tuteur', etc.
            ))
            print(f"✅ Lien parent-élève créé avec succès")
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*50)
        print("🎉 COMPTE PARENT DE TEST CRÉÉ AVEC SUCCÈS !")
        print("="*50)
        print(f"👤 Identifiant : {parent_username}")
        print(f"🔑 Mot de passe : {parent_password}")
        print(f"👨‍👩‍👧 Enfant lié : {student_name}")
        print("="*50)
        print("\nVous pouvez maintenant vous connecter avec ces identifiants !")

if __name__ == '__main__':
    create_test_parent()