from flask_login import UserMixin
from werkzeug.security import check_password_hash
import sqlite3

class User(UserMixin):
    def __init__(self, id, uuid, school_id, username, password_hash, role, full_name, email, phone, photo_path, active):
        self.id = id
        self.uuid = uuid
        self.school_id = school_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.full_name = full_name
        self.email = email
        self.phone = phone
        self.photo_path = photo_path
        self._active = bool(active)  # Attribut interne pour éviter le conflit avec UserMixin
    
    # On redéfinit la propriété is_active pour qu'elle utilise notre attribut interne
    @property
    def is_active(self):
        return self._active

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_id(user_id):
        from app import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row['id'],
                uuid=row['uuid'],
                school_id=row['school_id'],
                username=row['username'],
                password_hash=row['password_hash'],
                role=row['role'],
                full_name=row['full_name'],
                email=row['email'],
                phone=row['phone'],
                photo_path=row['photo_path'],
                active=row['is_active']  # On mappe la colonne 'is_active' vers le paramètre 'active'
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        from app import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row['id'],
                uuid=row['uuid'],
                school_id=row['school_id'],
                username=row['username'],
                password_hash=row['password_hash'],
                role=row['role'],
                full_name=row['full_name'],
                email=row['email'],
                phone=row['phone'],
                photo_path=row['photo_path'],
                active=row['is_active']  # On mappe la colonne 'is_active' vers le paramètre 'active'
            )
        return None

class Student:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @staticmethod
    def get_all(school_id):
        from app import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, c.label as class_name, l.name as level_name
            FROM students s
            LEFT JOIN enrollments e ON s.id = e.student_id AND e.status = 'active'
            LEFT JOIN classes c ON e.class_id = c.id
            LEFT JOIN levels l ON c.level_id = l.id
            WHERE s.school_id = ?
            ORDER BY s.last_name, s.first_name
        """, (school_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Student(**dict(row)) for row in rows]
    
    @staticmethod
    def get_by_id(student_id):
        from app import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cursor.fetchone()
        conn.close()
        return Student(**dict(row)) if row else None