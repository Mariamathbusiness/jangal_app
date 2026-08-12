import sqlite3
import os

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Ajout de la colonne director_name si elle n'existe pas
    cursor.execute("ALTER TABLE schools ADD COLUMN director_name TEXT DEFAULT 'Le Directeur';")
    conn.commit()
    print("✅ Colonne 'director_name' ajoutée avec succès (ou existait déjà).")
except sqlite3.OperationalError:
    print("ℹ️ La colonne 'director_name' existe déjà.")

# Création du dossier pour les logos s'il n'existe pas
logo_dir = os.path.join('app', 'static', 'uploads', 'logos')
os.makedirs(logo_dir, exist_ok=True)
print(f"✅ Dossier de logos créé : {logo_dir}")

conn.close()