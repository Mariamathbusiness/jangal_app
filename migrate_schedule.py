import sqlite3
import os

db_path = 'jangal.db'

if not os.path.exists(db_path):
    print("❌ Base de données non trouvée.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Renommer l'ancienne table
        cursor.execute("ALTER TABLE schedules RENAME TO schedules_old;")
        
        # 2. Créer la nouvelle table avec la bonne structure
        cursor.execute("""
            CREATE TABLE schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                class_id INTEGER,
                subject_id INTEGER,
                teacher_id INTEGER,
                day_of_week INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                room TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        print("✅ Table 'schedules' mise à jour avec succès !")
        print("💡 Vous pouvez maintenant supprimer manuellement la table 'schedules_old' via un outil SQLite si vous le souhaitez, mais ce n'est pas obligatoire.")
        
    except sqlite3.OperationalError as e:
        if "no such table: schedules" in str(e):
            # La table n'existait pas encore, on la crée simplement
            cursor.execute("""
                CREATE TABLE schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    class_id INTEGER,
                    subject_id INTEGER,
                    teacher_id INTEGER,
                    day_of_week INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    room TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            print("✅ Table 'schedules' créée avec succès !")
        else:
            print(f"❌ Erreur : {e}")
            
    conn.close()