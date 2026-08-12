import sqlite3
import os

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            UNIQUE(teacher_id, subject_id)
        )
    """)
    conn.commit()
    print("✅ Table 'teacher_subjects' créée avec succès !")
except Exception as e:
    print(f"❌ Erreur : {e}")
finally:
    conn.close()