import sqlite3
import os

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE schools ADD COLUMN start_date TEXT DEFAULT '2024-01-01';")
    cursor.execute("ALTER TABLE schools ADD COLUMN end_date TEXT DEFAULT '2025-12-31';")
    cursor.execute("ALTER TABLE schools ADD COLUMN status TEXT DEFAULT 'active';")
    conn.commit()
    print("✅ Colonnes 'start_date', 'end_date' et 'status' ajoutées à la table 'schools'.")
except sqlite3.OperationalError:
    print("ℹ️ Les colonnes existent déjà.")

# S'assurer qu'il y a au moins une école par défaut pour le super admin
cursor.execute("SELECT COUNT(id) FROM schools")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
        INSERT INTO schools (id, uuid, name, director_name, address, phone, email, start_date, end_date, status)
        VALUES (1, 'uuid-super', 'Établissement Principal', 'Le Directeur', 'Adresse par défaut', '000000000', 'contact@ecole.com', '2024-01-01', '2025-12-31', 'active')
    """)
    conn.commit()
    print("✅ École par défaut créée (ID: 1).")

conn.close()