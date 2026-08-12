import sqlite3

db_path = 'jangal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS adhesions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    school_name TEXT NOT NULL,
    school_type TEXT NOT NULL,
    student_count TEXT NOT NULL,
    address TEXT NOT NULL,
    creation_year TEXT,
    contact_name TEXT NOT NULL,
    contact_role TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    contact_email TEXT,
    current_system TEXT,
    challenges TEXT,
    features_interest TEXT,
    start_timeline TEXT,
    has_computer TEXT,
    message TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
print("✅ Table 'adhesions' créée avec succès !")
conn.close()