import sqlite3
import os

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE grades ADD COLUMN term TEXT DEFAULT 'Annuel';")
    conn.commit()
    print("✅ Colonne 'term' ajoutée à la table 'grades'.")
    print("ℹ️ Les notes existantes sont marquées comme 'Annuel' par défaut.")
except sqlite3.OperationalError:
    print("ℹ️ La colonne 'term' existe déjà.")

conn.close()