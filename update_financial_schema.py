import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def update_financial_schema():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL manquant. Ajoutez-le temporairement dans votre .env")
        return
    
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    print("✅ Connexion à la base de données Render...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("🔧 Création des tables financières...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_rates (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                school_id INTEGER NOT NULL REFERENCES schools(id),
                hourly_rate DECIMAL(10,2) NOT NULL,
                effective_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teaching_hours (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                school_id INTEGER NOT NULL REFERENCES schools(id),
                class_id INTEGER REFERENCES classes(id),
                subject_id INTEGER REFERENCES subjects(id),
                hours_count DECIMAL(5,2) NOT NULL,
                teaching_date DATE NOT NULL,
                academic_year_id INTEGER REFERENCES academic_years(id),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_payments (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                school_id INTEGER NOT NULL REFERENCES schools(id),
                amount DECIMAL(10,2) NOT NULL,
                payment_date DATE NOT NULL,
                payment_method TEXT,
                receipt_number TEXT,
                period_start DATE,
                period_end DATE,
                comment TEXT,
                received_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                school_id INTEGER NOT NULL REFERENCES schools(id),
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                expense_date DATE NOT NULL,
                payment_method TEXT,
                receipt_path TEXT,
                approved_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("🎉 Toutes les tables financières ont été créées avec succès !")
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    update_financial_schema()