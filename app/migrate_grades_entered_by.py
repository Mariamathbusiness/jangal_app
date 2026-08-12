import sqlite3

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE grades ADD COLUMN entered_by INTEGER;")
    conn.commit()
    print("✅ Colonne 'entered_by' ajoutée avec succès à la table 'grades'.")
except sqlite3.OperationalError:
    print("ℹ️ La colonne 'entered_by' existe déjà.")

conn.close()