import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import get_db

parent_bp = Blueprint('parent', __name__, template_folder='../templates/parent')

@parent_bp.route('/dashboard')
@login_required
def dashboard():
    # Vérifier que l'utilisateur est bien un parent
    if current_user.role != 'parent':
        flash("Accès réservé aux parents.", "danger")
        return redirect(url_for('admin.dashboard'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Récupérer les IDs des enfants liés à ce parent (stockés en JSON dans la table parents)
    cursor.execute("SELECT student_ids FROM parents WHERE user_id = ?", (current_user.id,))
    parent_record = cursor.fetchone()
    
    children = []
    if parent_record and parent_record['student_ids']:
        # Convertir la chaîne JSON en liste Python
        student_ids = json.loads(parent_record['student_ids'])
        
        if student_ids:
            # Récupérer les infos de ces enfants
            placeholders = ','.join('?' * len(student_ids))
            cursor.execute(f"""
                SELECT s.id, s.first_name, s.last_name, s.matricule, s.photo_path,
                       c.label as class_name, l.name as level_name
                FROM students s
                JOIN enrollments e ON s.id = e.student_id
                JOIN classes c ON e.class_id = c.id
                JOIN levels l ON c.level_id = l.id
                WHERE s.id IN ({placeholders}) AND e.status = 'active'
            """, student_ids)
            children = cursor.fetchall()
            
    conn.close()
    return render_template('parent/dashboard.html', children=children)

@parent_bp.route('/child/<int:student_id>')
@login_required
def child_details(student_id):
    # Sécurité : vérifier que cet enfant appartient bien à ce parent
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT student_ids FROM parents WHERE user_id = ?", (current_user.id,))
    parent_record = cursor.fetchone()
    
    if not parent_record or not parent_record['student_ids']:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('parent.dashboard'))
        
    student_ids = json.loads(parent_record['student_ids'])
    if str(student_id) not in [str(sid) for sid in student_ids]:
        flash("Vous n'êtes pas autorisé à voir les informations de cet élève.", "danger")
        return redirect(url_for('parent.dashboard'))

    # Récupérer les détails de l'enfant
    cursor.execute("""
        SELECT s.first_name, s.last_name, c.label as class_name
        FROM students s
        JOIN enrollments e ON s.id = e.student_id
        JOIN classes c ON e.class_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    child = cursor.fetchone()
        # Récupérer les moyennes par matière pour le trimestre en cours (par défaut Trimestre 1)
    current_term = request.args.get('term', 'Trimestre 1')
    
    cursor.execute("""
        SELECT sub.name as subject_name, 
               ROUND(SUM(g.grade_value * g.coefficient) / SUM(g.coefficient), 2) as average
        FROM grades g
        JOIN subjects sub ON g.subject_id = sub.id
        JOIN enrollments e ON g.enrollment_id = e.id
        WHERE e.student_id = ? AND g.term = ?
        GROUP BY sub.id
    """, (student_id, current_term))
    grades = cursor.fetchall()

    # Récupérer les dernières notes (moyennes par matière)
    cursor.execute("""
        SELECT sub.name as subject_name, 
               ROUND(AVG(g.grade_value), 2) as average
        FROM grades g
        JOIN subjects sub ON g.subject_id = sub.id
        WHERE g.enrollment_id = (SELECT id FROM enrollments WHERE student_id = ?)
        GROUP BY sub.id
    """, (student_id,))
    grades = cursor.fetchall()

    # Récupérer les derniers paiements
    cursor.execute("""
        SELECT receipt_number, amount, payment_date, payment_method
        FROM payments
        WHERE student_id = ?
        ORDER BY payment_date DESC
        LIMIT 5
    """, (student_id,))
    payments = cursor.fetchall()
    
    conn.close()
    
    return render_template('parent/child_details.html', child=child, grades=grades, payments=payments)