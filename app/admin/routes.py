import os
import uuid
import random
import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from app.admin.forms import (AcademicYearForm, LevelForm, ClassForm, StudentForm, SubjectForm, 
                             SchoolSettingsForm, SuperAdminSchoolForm, UserForm, 
                             WhatsAppNotificationForm, BulkBulletinForm)
from app import get_db, execute_query
from app.whatsapp_service import WhatsAppService

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def get_current_academic_year(school_id=1):
    query = "SELECT id, label FROM academic_years WHERE school_id = ? AND is_current = 1 LIMIT 1"
    cursor, conn = execute_query(query, (school_id,))
    year = cursor.fetchone()
    conn.close()
    return year


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role in ['parent', 'teacher']:
            flash("Accès réservé à l'administration (Directeur/Admin).", "danger")
            if current_user.role == 'teacher':
                return redirect(url_for('pedagogical.dashboard'))
            return redirect(url_for('parent.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


from functools import wraps
from flask import abort

# --- DÉCORATEUR DE SÉCURITÉ SUPER ADMIN ---
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if getattr(current_user, 'role', None) != 'super_admin':
            flash("⛔ Accès strictement réservé au Super Administrateur.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# TABLEAU DE BORD
# ============================================================
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    stats = {'students': 0, 'classes': 0, 'teachers': 0}
    
    if year_id:
        query = "SELECT COUNT(DISTINCT e.student_id) as count FROM enrollments e WHERE e.academic_year_id = ? AND e.status = 'active'"
        cursor, conn = execute_query(query, (year_id,))
        result = cursor.fetchone()
        stats['students'] = result['count'] if result else 0
        conn.close()
        
    query = "SELECT COUNT(id) as count FROM classes"
    cursor, conn = execute_query(query, ())
    result = cursor.fetchone()
    stats['classes'] = result['count'] if result else 0
    conn.close()
    
    query = "SELECT COUNT(id) as count FROM users WHERE role = 'teacher'"
    cursor, conn = execute_query(query, ())
    result = cursor.fetchone()
    stats['teachers'] = result['count'] if result else 0
    conn.close()
    
    # Note : si votre template est dans un dossier admin, utilisez 'admin/dashboard.html'
    return render_template('dashboard.html', stats=stats, current_year=current_year)


# ============================================================
# 1. ANNÉES SCOLAIRES
# ============================================================
@admin_bp.route('/years', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_years():
    form = AcademicYearForm()
    
    if form.validate_on_submit():
        if form.is_current.data:
            query = "UPDATE academic_years SET is_current = 0 WHERE school_id = ?"
            cursor, conn = execute_query(query, (current_user.school_id or 1,))
            conn.commit()
        
        query = """INSERT INTO academic_years (uuid, school_id, label, start_date, end_date, is_current)
                   VALUES (?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), current_user.school_id or 1, form.label.data,
            form.start_date.data.strftime('%Y-%m-%d'), form.end_date.data.strftime('%Y-%m-%d'),
            1 if form.is_current.data else 0
        ))
        conn.commit()
        flash('Année académique ajoutée avec succès.', 'success')
        return redirect(url_for('admin.manage_years'))
    
    cursor, conn = execute_query("SELECT * FROM academic_years ORDER BY start_date DESC", ())
    years = cursor.fetchall()
    conn.close()
    return render_template('admin/years.html', form=form, years=years)

@admin_bp.route('/years/set_current/<int:year_id>')
@login_required
@admin_required
def set_current_year(year_id):
    query = "UPDATE academic_years SET is_current = 0 WHERE school_id = ?"
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    conn.commit()
    
    query = "UPDATE academic_years SET is_current = 1 WHERE id = ? AND school_id = ?"
    cursor, conn = execute_query(query, (year_id, current_user.school_id or 1))
    conn.commit()
    conn.close()
    
    flash('Année en cours mise à jour.', 'success')
    return redirect(url_for('admin.manage_years'))


# ============================================================
# 2. NIVEAUX
# ============================================================
@admin_bp.route('/levels', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_levels():
    form = LevelForm()
    
    if form.validate_on_submit():
        query = "INSERT INTO levels (uuid, school_id, name, level_type) VALUES (?, ?, ?, ?)"
        cursor, conn = execute_query(query, (str(uuid.uuid4()), current_user.school_id or 1, form.name.data, form.level_type.data))
        conn.commit()
        flash('Niveau ajouté avec succès.', 'success')
        return redirect(url_for('admin.manage_levels'))
    
    query = "SELECT * FROM levels WHERE school_id = ?"
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    levels = cursor.fetchall()
    conn.close()
    return render_template('admin/levels.html', form=form, levels=levels)


# ============================================================
# 3. CLASSES
# ============================================================
@admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_classes():
    form = ClassForm()
    
    query = "SELECT id, name FROM levels WHERE school_id = ?"
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    form.level_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        query = "INSERT INTO classes (uuid, level_id, label, room, capacity) VALUES (?, ?, ?, ?, ?)"
        cursor, conn = execute_query(query, (str(uuid.uuid4()), form.level_id.data, form.label.data, form.room.data, form.capacity.data))
        conn.commit()
        flash('Classe ajoutée avec succès.', 'success')
        return redirect(url_for('admin.manage_classes'))
    
    query = """SELECT c.id, c.label, c.room, c.capacity, l.name as level_name 
               FROM classes c LEFT JOIN levels l ON c.level_id = l.id ORDER BY c.label ASC"""
    cursor, conn = execute_query(query, ())
    classes = cursor.fetchall()
    conn.close()
    return render_template('admin/classes.html', form=form, classes=classes)


# ============================================================
# 4. ÉLÈVES
# ============================================================
@admin_bp.route('/students', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_students():
    form = StudentForm()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    cursor, conn = execute_query("SELECT id, label FROM classes ORDER BY label ASC", ())
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        matricule = form.matricule.data.strip() if form.matricule.data else ""
        if not matricule:
            year_prefix = current_year['label'][:4] if current_year else '2024'
            while True:
                new_matricule = f"ELV-{year_prefix}-{random.randint(1000, 9999)}"
                cursor, conn = execute_query("SELECT id FROM students WHERE matricule = ?", (new_matricule,))
                if not cursor.fetchone():
                    matricule = new_matricule
                    conn.close()
                    break
                conn.close()
        
        photo_filename = None
        if form.photo.data:
            photo_filename = f"{uuid.uuid4().hex}_{secure_filename(form.photo.data.filename)}"
            form.photo.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos', photo_filename))
        
        query = """INSERT INTO students (uuid, school_id, matricule, last_name, first_name, date_of_birth, gender, photo_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), current_user.school_id or 1, matricule, form.last_name.data,
            form.first_name.data, form.date_of_birth.data.strftime('%Y-%m-%d'), form.gender.data, photo_filename
        ))
        student_id = cursor.lastrowid
        
        if year_id:
            query = """INSERT INTO enrollments (uuid, student_id, class_id, academic_year_id, status)
                       VALUES (?, ?, ?, ?, 'active')"""
            cursor, conn = execute_query(query, (str(uuid.uuid4()), student_id, form.class_id.data, year_id))
        
        conn.commit()
        conn.close()
        flash(f'Élève {form.last_name.data} inscrit avec succès (Matricule: {matricule}).', 'success')
        return redirect(url_for('admin.manage_students'))
    
    if year_id:
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name, s.gender, s.photo_path, c.label as class_name
                   FROM students s
                   JOIN enrollments e ON s.id = e.student_id
                   LEFT JOIN classes c ON e.class_id = c.id
                   WHERE s.school_id = ? AND e.academic_year_id = ? AND e.status = 'active'
                   ORDER BY s.last_name ASC"""
        cursor, conn = execute_query(query, (current_user.school_id or 1, year_id))
    else:
        query = "SELECT id, matricule, first_name, last_name, gender, photo_path, '' as class_name FROM students WHERE school_id = ?"
        cursor, conn = execute_query(query, (current_user.school_id or 1,))
        
    students = cursor.fetchall()
    conn.close()
    return render_template('admin/students.html', form=form, students=students, current_year=current_year)


# ============================================================
# 5. MATIÈRES
# ============================================================
@admin_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_subjects():
    form = SubjectForm()
    
    if form.validate_on_submit():
        query = """INSERT INTO subjects (uuid, school_id, name, code, coefficient, credits, is_ue)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), current_user.school_id or 1, form.name.data, form.code.data,
            form.coefficient.data, form.credits.data, 1 if form.is_ue.data else 0
        ))
        conn.commit()
        conn.close()
        flash('Matière ajoutée avec succès.', 'success')
        return redirect(url_for('admin.manage_subjects'))
    
    query = "SELECT * FROM subjects WHERE school_id = ? ORDER BY name ASC"
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    subjects = cursor.fetchall()
    conn.close()
    return render_template('admin/subjects.html', form=form, subjects=subjects)


# ============================================================
# 6. IMPORT EXCEL
# ============================================================
@admin_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_students():
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None

    if not year_id:
        flash("Veuillez d'abord définir une année scolaire en cours.", "danger")
        return redirect(url_for('admin.manage_years'))

    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith('.xlsx'):
            flash("Veuillez sélectionner un fichier Excel valide (.xlsx).", "danger")
            return redirect(url_for('admin.import_students'))

        try:
            df = pd.read_excel(file)
            required_cols = ['Matricule', 'Nom', 'Prenom', 'Date_Naissance', 'Genre', 'Classe']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                flash(f"Colonnes manquantes dans le fichier : {', '.join(missing_cols)}", "danger")
                return redirect(url_for('admin.import_students'))

            successes = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    matricule = str(row['Matricule']).strip()
                    last_name = str(row['Nom']).strip().upper()
                    first_name = str(row['Prenom']).strip().capitalize()
                    
                    dob = row['Date_Naissance']
                    if isinstance(dob, pd.Timestamp):
                        dob_str = dob.strftime('%Y-%m-%d')
                    else:
                        dob_str = datetime.strptime(str(dob), '%Y-%m-%d').strftime('%Y-%m-%d')
                    
                    gender = str(row['Genre']).strip().upper()
                    if gender not in ['M', 'F']:
                        errors.append(f"Ligne {index+2}: Genre invalide ('{gender}'). Doit être 'M' ou 'F'.")
                        continue

                    class_name = str(row['Classe']).strip()

                    cursor, conn = execute_query("SELECT id FROM students WHERE matricule = ?", (matricule,))
                    if cursor.fetchone():
                        errors.append(f"Ligne {index+2}: Le matricule '{matricule}' existe déjà.")
                        conn.close()
                        continue
                    conn.close()

                    cursor, conn = execute_query("SELECT id FROM classes WHERE label = ?", (class_name,))
                    class_row = cursor.fetchone()
                    conn.close()
                    if not class_row:
                        errors.append(f"Ligne {index+2}: La classe '{class_name}' n'existe pas.")
                        continue
                    class_id = class_row['id']

                    query = """INSERT INTO students (uuid, school_id, matricule, last_name, first_name, date_of_birth, gender)
                               VALUES (?, ?, ?, ?, ?, ?, ?)"""
                    cursor, conn = execute_query(query, (str(uuid.uuid4()), current_user.school_id or 1, matricule, last_name, first_name, dob_str, gender))
                    student_id = cursor.lastrowid

                    query = """INSERT INTO enrollments (uuid, student_id, class_id, academic_year_id, status)
                               VALUES (?, ?, ?, ?, 'active')"""
                    cursor, conn = execute_query(query, (str(uuid.uuid4()), student_id, class_id, year_id))

                    successes += 1
                    conn.commit()
                    conn.close()
                except Exception as e:
                    errors.append(f"Ligne {index+2}: Erreur inattendue ({str(e)})")

            if successes > 0:
                flash(f"✅ Import réussi : {successes} élève(s) ajouté(s).", "success")
            if errors:
                error_msg = "⚠️ Erreurs rencontrées :<br>" + "<br>".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"<br>... et {len(errors) - 5} autres erreurs."
                flash(error_msg, "warning")

        except Exception as e:
            flash(f"Erreur lors de la lecture du fichier : {str(e)}", "danger")
        
        return redirect(url_for('admin.import_students'))

    return render_template('admin/import_students.html', current_year=current_year)

@admin_bp.route('/download_template')
@login_required
@admin_required
def download_template():
    df = pd.DataFrame(columns=['Matricule', 'Nom', 'Prenom', 'Date_Naissance', 'Genre', 'Classe'])
    df.loc[0] = ['ELV-2024-0001', 'DIALLO', 'Aminata', '2010-05-15', 'F', '6ème A']
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Modele')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='modele_import_eleves.xlsx'
    )


# ============================================================
# 7. GESTION DES PARENTS
# ============================================================
@admin_bp.route('/parents', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_parents():
    if request.method == 'POST':
        action = request.form.get('action')
        parent_id = request.form.get('parent_id')
        
        if action == 'create':
            username = request.form.get('username')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            query = """INSERT INTO users (uuid, school_id, username, password_hash, role, full_name, email, phone)
                       VALUES (?, ?, ?, ?, 'parent', ?, ?, ?)"""
            cursor, conn = execute_query(query, (str(uuid.uuid4()), current_user.school_id or 1, username, 
                  generate_password_hash(password), full_name, email, phone))
            conn.commit()
            conn.close()
            flash(f'Parent {full_name} créé avec succès.', 'success')
            
        elif action == 'link':
            parent_user_id = int(parent_id)
            selected_students = request.form.getlist('students')
            
            if selected_students:
                query = """INSERT OR REPLACE INTO parents (uuid, user_id, student_ids, relationship)
                           VALUES (?, ?, ?, ?)"""
                cursor, conn = execute_query(query, (str(uuid.uuid4()), parent_user_id, json.dumps([int(s) for s in selected_students]), 'parent'))
            else:
                cursor, conn = execute_query("DELETE FROM parents WHERE user_id = ?", (parent_user_id,))
            
            conn.commit()
            conn.close()
            flash('Lien parent-enfants mis à jour.', 'success')
        
        return redirect(url_for('admin.manage_parents'))
    
    query = """SELECT u.id as user_id, u.username, u.full_name, u.email, u.phone, p.student_ids
               FROM users u
               LEFT JOIN parents p ON u.id = p.user_id
               WHERE u.role = 'parent' AND u.school_id = ?
               ORDER BY u.full_name"""
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    parents = cursor.fetchall()
    
    current_year = get_current_academic_year(current_user.school_id or 1)
    if current_year:
        query = """SELECT s.id, s.first_name, s.last_name, s.matricule, c.label as class_name
                   FROM students s
                   JOIN enrollments e ON s.id = e.student_id
                   LEFT JOIN classes c ON e.class_id = c.id
                   WHERE e.academic_year_id = ? AND e.status = 'active'
                   ORDER BY s.last_name"""
        cursor, conn = execute_query(query, (current_year['id'],))
    else:
        cursor, conn = execute_query("SELECT id, first_name, last_name, matricule FROM students ORDER BY last_name", ())
    
    all_students = cursor.fetchall()
    conn.close()
    
    return render_template('admin/parents.html', parents=parents, all_students=all_students)

@admin_bp.route('/parents/link/<int:parent_user_id>')
@login_required
@admin_required
def link_parent(parent_user_id):
    cursor, conn = execute_query("SELECT id, username, full_name FROM users WHERE id = ?", (parent_user_id,))
    parent = cursor.fetchone()
    
    cursor, conn = execute_query("SELECT student_ids FROM parents WHERE user_id = ?", (parent_user_id,))
    parent_record = cursor.fetchone()
    linked_ids = []
    if parent_record and parent_record['student_ids']:
        linked_ids = json.loads(parent_record['student_ids'])
    
    current_year = get_current_academic_year(current_user.school_id or 1)
    if current_year:
        query = """SELECT s.id, s.first_name, s.last_name, s.matricule, c.label as class_name
                   FROM students s
                   JOIN enrollments e ON s.id = e.student_id
                   LEFT JOIN classes c ON e.class_id = c.id
                   WHERE e.academic_year_id = ? AND e.status = 'active'
                   ORDER BY s.last_name"""
        cursor, conn = execute_query(query, (current_year['id'],))
    else:
        cursor, conn = execute_query("SELECT id, first_name, last_name, matricule FROM students ORDER BY last_name", ())
    
    all_students = cursor.fetchall()
    conn.close()
    
    return render_template('admin/link_parent.html', parent=parent, all_students=all_students, linked_ids=linked_ids)


# ============================================================
# 8. GESTION DES ENSEIGNANTS ET MATIÈRES
# ============================================================
@admin_bp.route('/teachers', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_teachers():
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        selected_subjects = request.form.getlist('subjects')
        
        cursor, conn = execute_query("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        for subject_id in selected_subjects:
            cursor, conn = execute_query("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)", (teacher_id, subject_id))
            
        conn.commit()
        conn.close()
        flash('Matières attribuées à l\'enseignant avec succès.', 'success')
        return redirect(url_for('admin.manage_teachers'))
    
    cursor, conn = execute_query("SELECT id, username, full_name FROM users WHERE role = 'teacher' ORDER BY full_name", ())
    teachers = cursor.fetchall()
    
    cursor, conn = execute_query("SELECT id, name FROM subjects ORDER BY name", ())
    all_subjects = cursor.fetchall()
    
    editing_teacher_id = request.args.get('teacher_id', type=int)
    editing_teacher = None
    assigned_subject_ids = []
    
    if editing_teacher_id:
        cursor, conn = execute_query("SELECT id, username, full_name FROM users WHERE id = ?", (editing_teacher_id,))
        editing_teacher = cursor.fetchone()
        
        cursor, conn = execute_query("SELECT subject_id FROM teacher_subjects WHERE teacher_id = ?", (editing_teacher_id,))
        assigned_subject_ids = [row['subject_id'] for row in cursor.fetchall()]

    conn.close()
    return render_template('admin/teachers.html', teachers=teachers, all_subjects=all_subjects, 
                           editing_teacher=editing_teacher, assigned_subject_ids=assigned_subject_ids)


# ============================================================
# 9. PARAMÈTRES DE L'ÉCOLE
# ============================================================
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def school_settings():
    form = SchoolSettingsForm()
    school_id = current_user.school_id or 1
    
    cursor, conn = execute_query("SELECT * FROM schools WHERE id = ?", (school_id,))
    school = cursor.fetchone()
    
    if school:
        school = dict(school)
    
    if form.validate_on_submit():
        logo_filename = school['logo_path'] if school else None
        
        if form.logo.data:
            if logo_filename:
                old_logo_path = os.path.join(current_app.root_path, 'static', 'uploads', 'logos', logo_filename)
                if os.path.exists(old_logo_path):
                    os.remove(old_logo_path)
            
            logo_filename = f"{uuid.uuid4().hex}_{secure_filename(form.logo.data.filename)}"
            logo_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            os.makedirs(logo_dir, exist_ok=True)
            form.logo.data.save(os.path.join(logo_dir, logo_filename))
        
        if school:
            query = """UPDATE schools SET name = ?, director_name = ?, address = ?, phone = ?, email = ?, logo_path = ?
                       WHERE id = ?"""
            cursor, conn = execute_query(query, (form.name.data, form.director_name.data, form.address.data, 
                  form.phone.data, form.email.data, logo_filename, school_id))
        else:
            query = """INSERT INTO schools (id, uuid, name, director_name, address, phone, email, logo_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor, conn = execute_query(query, (school_id, str(uuid.uuid4()), form.name.data, form.director_name.data, 
                  form.address.data, form.phone.data, form.email.data, logo_filename))
            
        conn.commit()
        conn.close()
        flash('Paramètres de l\'école enregistrés avec succès !', 'success')
        return redirect(url_for('admin.school_settings'))
    
    if school:
        form.name.data = school.get('name')
        form.director_name.data = school.get('director_name') or 'Le Directeur'
        form.address.data = school.get('address')
        form.phone.data = school.get('phone')
        form.email.data = school.get('email')

    conn.close()
    return render_template('admin/school_settings.html', form=form, current_logo=school.get('logo_path') if school else None)


# ============================================================
# 10. GESTION MULTI-ÉCOLES (SUPER ADMIN)
# ============================================================
@admin_bp.route('/super_admin/schools', methods=['GET', 'POST'])
@login_required
@super_admin_required
def manage_schools():
    form = SuperAdminSchoolForm()
    
    if form.validate_on_submit():
        school_id = request.form.get('school_id', type=int)
        
        if school_id:
            query = """UPDATE schools SET name = ?, director_name = ?, address = ?, phone = ?, email = ?, 
                       start_date = ?, end_date = ?, status = ? WHERE id = ?"""
            cursor, conn = execute_query(query, (
                form.name.data, form.director_name.data, form.address.data, form.phone.data, form.email.data,
                form.start_date.data.strftime('%Y-%m-%d'), form.end_date.data.strftime('%Y-%m-%d'), 
                form.status.data, school_id
            ))
            flash('Établissement mis à jour avec succès.', 'success')
        else:
            query = """INSERT INTO schools (uuid, name, director_name, address, phone, email, start_date, end_date, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor, conn = execute_query(query, (
                str(uuid.uuid4()), form.name.data, form.director_name.data, form.address.data, 
                form.phone.data, form.email.data, form.start_date.data.strftime('%Y-%m-%d'), 
                form.end_date.data.strftime('%Y-%m-%d'), form.status.data
            ))
            flash('Nouvel établissement créé avec succès.', 'success')
            
        conn.commit()
        conn.close()
        return redirect(url_for('admin.manage_schools'))

    cursor, conn = execute_query("SELECT id, name, director_name, start_date, end_date, status FROM schools ORDER BY id ASC", ())
    schools = cursor.fetchall()
    
    edit_id = request.args.get('edit', type=int)
    if edit_id:
        cursor, conn = execute_query("SELECT * FROM schools WHERE id = ?", (edit_id,))
        school_to_edit = cursor.fetchone()
        if school_to_edit:
            school_to_edit = dict(school_to_edit)
            form.name.data = school_to_edit['name']
            form.director_name.data = school_to_edit['director_name']
            form.address.data = school_to_edit['address']
            form.phone.data = school_to_edit['phone']
            form.email.data = school_to_edit['email']
            form.start_date.data = datetime.strptime(school_to_edit['start_date'], '%Y-%m-%d').date()
            form.end_date.data = datetime.strptime(school_to_edit['end_date'], '%Y-%m-%d').date()
            form.status.data = school_to_edit['status']
            form.submit.label.text = "🔄 Mettre à jour l'établissement"
    else:
        form.submit.label.text = "➕ Créer un nouvel établissement"

    conn.close()
    return render_template('admin/super_admin_schools.html', form=form, schools=schools, edit_id=edit_id)

@admin_bp.route('/super_admin/schools/delete/<int:school_id>')
@login_required
@super_admin_required
def delete_school(school_id):
    if school_id == 1:
        flash("L'établissement principal (ID 1) ne peut pas être supprimé.", "danger")
    else:
        cursor, conn = execute_query("DELETE FROM schools WHERE id = ?", (school_id,))
        conn.commit()
        conn.close()
        flash("Établissement supprimé.", "success")
    return redirect(url_for('admin.manage_schools'))


# ============================================================
# 11. GESTION DES UTILISATEURS
# ============================================================
@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_users():
    form = UserForm()
    
    # 🔒 SÉCURITÉ : Filtrer les rôles disponibles selon l'utilisateur connecté
    if current_user.role == 'super_admin':
        # Le Super Admin voit TOUS les rôles
        form.role.choices = [
            ('super_admin', 'Super Administrateur'),
            ('admin', 'Administrateur / Directeur'),
            ('teacher', 'Enseignant'),
            ('accountant', 'Comptable'),
            ('parent', 'Parent')
        ]
        # Il peut aussi choisir parmi toutes les écoles
        cursor, conn = execute_query("SELECT id, name FROM schools ORDER BY name ASC", ())
        form.school_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
        conn.close()
    else:
        # ❌ Un admin normal ne voit PAS le rôle "super_admin"
        form.role.choices = [
            ('admin', 'Administrateur / Directeur'),
            ('teacher', 'Enseignant'),
            ('accountant', 'Comptable'),
            ('parent', 'Parent')
        ]
        # Il ne peut créer des utilisateurs que dans SA propre école
        form.school_id.choices = [(current_user.school_id, "Mon Établissement")]
        form.school_id.data = current_user.school_id

    if form.validate_on_submit():
        user_id = request.form.get('user_id', type=int)
        
        # 🔒 SÉCURITÉ BACKEND : Empêcher l'escalade de privilèges
        if current_user.role != 'super_admin' and form.role.data == 'super_admin':
            flash("⛔ Action interdite : vous ne pouvez pas créer un Super Administrateur.", "danger")
            return redirect(url_for('admin.manage_users'))
        
        target_school_id = form.school_id.data if current_user.role == 'super_admin' else current_user.school_id

        if user_id:
            # --- MODIFICATION ---
            if form.password.data:
                query = """UPDATE users SET username = ?, password_hash = ?, full_name = ?, email = ?, phone = ?, role = ?, school_id = ?
                           WHERE id = ?"""
                cursor, conn = execute_query(query, (
                    form.username.data, generate_password_hash(form.password.data), form.full_name.data,
                    form.email.data, form.phone.data, form.role.data, target_school_id, user_id
                ))
            else:
                query = """UPDATE users SET username = ?, full_name = ?, email = ?, phone = ?, role = ?, school_id = ?
                           WHERE id = ?"""
                cursor, conn = execute_query(query, (
                    form.username.data, form.full_name.data, form.email.data,
                    form.phone.data, form.role.data, target_school_id, user_id
                ))
            flash('✅ Utilisateur mis à jour avec succès.', 'success')
        else:
            # --- CRÉATION ---
            if not form.password.data:
                flash('⚠️ Le mot de passe est obligatoire pour créer un nouvel utilisateur.', 'danger')
                return redirect(url_for('admin.manage_users'))
                
            query = """INSERT INTO users (uuid, school_id, username, password_hash, full_name, email, phone, role)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor, conn = execute_query(query, (
                str(uuid.uuid4()), target_school_id, form.username.data, 
                generate_password_hash(form.password.data), form.full_name.data, 
                form.email.data, form.phone.data, form.role.data
            ))
            flash('✅ Nouvel utilisateur créé avec succès.', 'success')
            
        conn.commit()
        conn.close()
        return redirect(url_for('admin.manage_users'))

    # Liste des utilisateurs (filtrée par école pour les admins normaux)
    if current_user.role == 'super_admin':
        query = """SELECT u.id, u.username, u.full_name, u.email, u.role, s.name as school_name
                   FROM users u LEFT JOIN schools s ON u.school_id = s.id
                   ORDER BY s.name, u.full_name ASC"""
        cursor, conn = execute_query(query, ())
    else:
        query = """SELECT u.id, u.username, u.full_name, u.email, u.role, 'Mon École' as school_name
                   FROM users u WHERE u.school_id = ?
                   ORDER BY u.full_name ASC"""
        cursor, conn = execute_query(query, (current_user.school_id,))
        
    users_list = cursor.fetchall()
    
    # Mode édition
    edit_id = request.args.get('edit', type=int)
    if edit_id:
        cursor, conn = execute_query("SELECT * FROM users WHERE id = ?", (edit_id,))
        user_to_edit = cursor.fetchone()
        if user_to_edit:
            user_to_edit = dict(user_to_edit)
            
            # 🔒 SÉCURITÉ : Un admin ne peut pas modifier un super_admin
            if current_user.role != 'super_admin' and user_to_edit['role'] == 'super_admin':
                flash("⛔ Action interdite : vous ne pouvez pas modifier un Super Administrateur.", "danger")
                conn.close()
                return redirect(url_for('admin.manage_users'))
            
            form.username.data = user_to_edit['username']
            form.full_name.data = user_to_edit['full_name']
            form.email.data = user_to_edit['email']
            form.phone.data = user_to_edit.get('phone', '')
            form.role.data = user_to_edit['role']
            form.school_id.data = user_to_edit['school_id']
            form.submit.label.text = "🔄 Mettre à jour l'utilisateur"
    else:
        form.submit.label.text = "➕ Créer un nouvel utilisateur"

    conn.close()
    return render_template('admin/users.html', form=form, users_list=users_list, edit_id=edit_id)

@admin_bp.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash("⚠️ Vous ne pouvez pas supprimer votre propre compte.", "danger")
    else:
        # 🔒 SÉCURITÉ : Vérifier que l'utilisateur cible existe et est accessible
        cursor, conn = execute_query("SELECT school_id, role FROM users WHERE id = ?", (user_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            flash("❌ Utilisateur introuvable.", "danger")
            conn.close()
            return redirect(url_for('admin.manage_users'))
        
        # Un admin normal ne peut pas supprimer un super_admin
        if current_user.role != 'super_admin' and target_user['role'] == 'super_admin':
            flash("⛔ Action interdite : vous ne pouvez pas supprimer un Super Administrateur.", "danger")
            conn.close()
            return redirect(url_for('admin.manage_users'))
        
        # Un admin normal ne peut supprimer que dans sa propre école
        if current_user.role != 'super_admin' and target_user['school_id'] != current_user.school_id:
            flash("⛔ Action non autorisée.", "danger")
            conn.close()
            return redirect(url_for('admin.manage_users'))
        
        cursor, conn = execute_query("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("✅ Utilisateur supprimé.", "success")
    
    return redirect(url_for('admin.manage_users'))


# ============================================================
# 12. MODULE NOTIFICATIONS WHATSAPP (UNITAIRE)
# ============================================================
@admin_bp.route('/whatsapp/send', methods=['GET', 'POST'])
@login_required
@admin_required
def send_whatsapp_notification():
    form = WhatsAppNotificationForm()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    if year_id:
        query = """SELECT s.id, s.first_name, s.last_name, s.matricule, u.phone as parent_phone
                   FROM students s
                   JOIN enrollments e ON s.id = e.student_id
                   LEFT JOIN parents par ON par.student_ids LIKE '%%' || CAST(s.id AS TEXT) || '%%'
                   LEFT JOIN users u ON par.user_id = u.id
                   WHERE e.academic_year_id = ? AND e.status = 'active'
                   ORDER BY s.last_name"""
        cursor, conn = execute_query(query, (year_id,))
    else:
        cursor, conn = execute_query("SELECT s.id, s.first_name, s.last_name, s.matricule, '' as parent_phone FROM students s", ())
    
    students = cursor.fetchall()
    form.student_id.choices = [(s['id'], f"{s['last_name']} {s['first_name']} ({s['matricule']})") for s in students]
    conn.close()
    
    if form.validate_on_submit():
        student_id = form.student_id.data
        message_type = form.message_type.data
        
        query = """SELECT s.first_name, s.last_name, c.label as class_name, u.phone as parent_phone
                   FROM students s
                   LEFT JOIN enrollments e ON s.id = e.student_id
                   LEFT JOIN classes c ON e.class_id = c.id
                   LEFT JOIN parents par ON par.student_ids LIKE '%%' || CAST(s.id AS TEXT) || '%%'
                   LEFT JOIN users u ON par.user_id = u.id
                   WHERE s.id = ?"""
        cursor, conn = execute_query(query, (student_id,))
        student = cursor.fetchone()
        
        if not student or not student['parent_phone']:
            flash("❌ Numéro de téléphone du parent non trouvé dans le système.", "danger")
            conn.close()
            return redirect(url_for('admin.send_whatsapp_notification'))
        
        whatsapp = WhatsAppService()
        success, msg = False, ""
        
        if message_type == 'bulletin':
            query = """SELECT ROUND(AVG(g.grade_value), 2) as avg
                       FROM grades g
                       WHERE g.enrollment_id = (SELECT id FROM enrollments WHERE student_id = ?)"""
            cursor, conn = execute_query(query, (student_id,))
            avg_result = cursor.fetchone()
            average = avg_result['avg'] if avg_result and avg_result['avg'] else 0.0
            decision = "ADMIS(E)" if average >= 10.0 else "AJOURNÉ(E)"
            
            success, msg = whatsapp.send_bulletin_summary(
                student['parent_phone'], 
                f"{student['last_name']} {student['first_name']}",
                student['class_name'], average, decision
            )
            
        elif message_type == 'absence':
            query = """SELECT date, status, comment FROM attendances
                       WHERE enrollment_id = (SELECT id FROM enrollments WHERE student_id = ?)
                       ORDER BY date DESC LIMIT 1"""
            cursor, conn = execute_query(query, (student_id,))
            attendance = cursor.fetchone()
            if attendance:
                success, msg = whatsapp.send_absence_alert(
                    student['parent_phone'], f"{student['last_name']} {student['first_name']}",
                    student['class_name'], attendance['date'], attendance['status'], attendance['comment']
                )
            else:
                msg = "Aucune absence enregistrée pour cet élève."
                
        elif message_type == 'payment':
            success, msg = whatsapp.send_payment_reminder(
                student['parent_phone'], f"{student['last_name']} {student['first_name']}",
                50000, datetime.now().strftime('%d/%m/%Y')
            )
            
        elif message_type == 'custom':
            success, msg = whatsapp.send_message(student['parent_phone'], form.custom_message.data)
            
        flash("✅ Message envoyé avec succès !" if success else f"❌ Échec de l'envoi : {msg}", "success" if success else "danger")
        
        conn.close()
        return redirect(url_for('admin.send_whatsapp_notification'))
    
    conn.close()
    return render_template('admin/whatsapp_notifications.html', form=form)


# ============================================================
# 13. RAPPELS DE PAIEMENT EN MASSE
# ============================================================
@admin_bp.route('/whatsapp/bulk_payment_reminders', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_payment_reminders():
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    if not year_id:
        flash("⚠️ Veuillez d'abord définir une année scolaire en cours.", "warning")
        return redirect(url_for('admin.manage_years'))
    
    query = """SELECT s.id, s.matricule, s.first_name, s.last_name,
               c.label as class_name, l.id as level_id,
               u.phone as parent_phone, u.full_name as parent_name
        FROM students s
        JOIN enrollments e ON s.id = e.student_id
        JOIN classes c ON e.class_id = c.id
        JOIN levels l ON c.level_id = l.id
        LEFT JOIN parents par ON par.student_ids LIKE '%%' || CAST(s.id AS TEXT) || '%%'
        LEFT JOIN users u ON par.user_id = u.id
        WHERE e.academic_year_id = ? AND e.status = 'active'
        ORDER BY s.last_name ASC"""
    cursor, conn = execute_query(query, (year_id,))
    students = cursor.fetchall()
    conn.close()
    
    students_overdue = []
    for student in students:
        query_fees = "SELECT COALESCE(SUM(amount), 0) as total_fees FROM fees WHERE level_id = ? AND academic_year_id = ?"
        cursor_fee, conn_fee = execute_query(query_fees, (student['level_id'], year_id))
        res_fee = cursor_fee.fetchone()
        amount_due = res_fee['total_fees'] if res_fee else 0
        conn_fee.close()
        
        query_paid = "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE student_id = ?"
        cursor_pay, conn_pay = execute_query(query_paid, (student['id'],))
        res_pay = cursor_pay.fetchone()
        amount_paid = res_pay['total_paid'] if res_pay else 0
        conn_pay.close()
        
        balance = amount_paid - amount_due
        
        if balance < 0 and student['parent_phone']:
            students_overdue.append({
                'student_id': student['id'],
                'matricule': student['matricule'],
                'full_name': f"{student['last_name']} {student['first_name']}",
                'class_name': student['class_name'],
                'parent_phone': student['parent_phone'],
                'parent_name': student['parent_name'] or 'Parent',
                'amount_due': amount_due,
                'amount_paid': amount_paid,
                'balance': balance
            })
    
    results = None
    if request.method == 'POST' and request.form.get('action') == 'send_reminders':
        whatsapp = WhatsAppService()
        results = {'success': [], 'failed': [], 'no_phone': []}
        
        for student in students_overdue:
            amount_to_pay = abs(student['balance'])
            
            message = f"""💰 *RAPPEL DE PAIEMENT - Jangal_App*

Bonjour {student['parent_name']},

Nous vous rappelons que le compte de votre enfant *{student['full_name']}* ({student['class_name']}) présente un solde débiteur.

📊 *Situation financière :*
• Total des frais : {student['amount_due']:,.0f} FCFA
• Montant déjà payé : {student['amount_paid']:,.0f} FCFA
• *Reste à payer : {amount_to_pay:,.0f} FCFA*

Merci de bien vouloir régulariser la situation auprès de la caisse dans les meilleurs délais.

Cordialement,
La Comptabilité"""
            
            success, msg = whatsapp.send_message(student['parent_phone'], message)
            
            if success:
                results['success'].append({
                    'name': student['full_name'],
                    'class': student['class_name'],
                    'amount': amount_to_pay,
                    'phone': student['parent_phone']
                })
            else:
                results['failed'].append({
                    'name': student['full_name'],
                    'class': student['class_name'],
                    'error': str(msg)
                })
        
        flash(f"✅ {len(results['success'])} rappel(s) envoyé(s) avec succès ! {'❌ ' + str(len(results['failed'])) + ' échec(s).' if results['failed'] else ''}", 
              "success" if results['success'] else "danger")
    
    return render_template('admin/bulk_payment_reminders.html', 
                          students_overdue=students_overdue,
                          results=results,
                          current_year=current_year)


# ============================================================
# 14. ENVOI GROUPÉ DES BULLETINS
# ============================================================
@admin_bp.route('/whatsapp/bulk_bulletins', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_bulletins():
    """Envoi groupé des récapitulatifs de bulletins par classe et période"""
    form = BulkBulletinForm()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    cursor, conn = execute_query("SELECT id, label FROM classes ORDER BY label ASC", ())
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]
    conn.close()
    
    results = None
    
    if form.validate_on_submit():
        class_id = form.class_id.data
        
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name,
                   c.label as class_name, u.phone as parent_phone, u.full_name as parent_name
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id
            LEFT JOIN parents par ON par.student_ids LIKE '%' || CAST(s.id AS TEXT) || '%'
            LEFT JOIN users u ON par.user_id = u.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
            ORDER BY s.last_name ASC"""
        cursor, conn = execute_query(query, (class_id, year_id))
        students = cursor.fetchall()
        
        whatsapp = WhatsAppService()
        results = {'success': [], 'failed': [], 'no_phone': []}
        
        for student in students:
            student_name = f"{student['last_name']} {student['first_name']}"
            
            query = """SELECT ROUND(AVG(g.grade_value), 2) as avg
                       FROM grades g
                       WHERE g.enrollment_id = (SELECT id FROM enrollments WHERE student_id = ?)"""
            cursor_avg, conn_avg = execute_query(query, (student['id'],))
            avg_result = cursor_avg.fetchone()
            conn_avg.close()
            average = avg_result['avg'] if avg_result and avg_result['avg'] else 0.0
            
            decision = "ADMIS(E)" if average >= 10.0 else "AJOURNÉ(E)"
            
            if not student['parent_phone']:
                results['no_phone'].append({
                    'name': student_name,
                    'matricule': student['matricule'],
                    'reason': 'Aucun numéro de parent enregistré'
                })
                continue
            
            success, msg = whatsapp.send_bulletin_summary(
                student['parent_phone'], 
                student_name,
                student['class_name'],
                average,
                decision
            )
            
            if success:
                results['success'].append({
                    'name': student_name,
                    'matricule': student['matricule'],
                    'average': average,
                    'phone': student['parent_phone']
                })
            else:
                results['failed'].append({
                    'name': student_name,
                    'matricule': student['matricule'],
                    'error': str(msg)
                })
                
        flash(f"✅ Envoi terminé : {len(results['success'])} succès, {len(results['failed'])} échecs, {len(results['no_phone'])} sans numéro.", 
              "warning" if results['failed'] or results['no_phone'] else "success")

    conn.close()
    return render_template('admin/bulk_bulletins.html', form=form, results=results, current_year=current_year)


# ============================================================
# FORMULAIRE D'ADHÉSION EN LIGNE (PUBLIC)
# ============================================================
@admin_bp.route('/adhesion', methods=['GET', 'POST'])
def adhesion_form():
    """Formulaire d'adhésion accessible publiquement"""
    if request.method == 'POST':
        features = request.form.getlist('features_interest')
        challenges = request.form.getlist('challenges')
        
        try:
            query = """INSERT INTO adhesions (uuid, school_name, school_type, student_count, address, 
                       creation_year, contact_name, contact_role, contact_phone, 
                       contact_email, current_system, challenges, features_interest, 
                       start_timeline, has_computer, message, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')"""
            cursor, conn = execute_query(query, (
                str(uuid.uuid4()),
                request.form.get('school_name'),
                request.form.get('school_type'),
                request.form.get('student_count'),
                request.form.get('address'),
                request.form.get('creation_year'),
                request.form.get('contact_name'),
                request.form.get('contact_role'),
                request.form.get('contact_phone'),
                request.form.get('contact_email'),
                request.form.get('current_system'),
                json.dumps(challenges),
                json.dumps(features),
                request.form.get('start_timeline'),
                request.form.get('has_computer'),
                request.form.get('message')
            ))
            adhesion_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash('✅ Votre demande a été enregistrée avec succès ! Nous vous recontactons sous 48h.', 'success')
            return redirect(url_for('admin.adhesion_confirmation', adhesion_id=adhesion_id))
        except Exception as e:
            conn.close()
            flash(f'❌ Erreur lors de l\'enregistrement : {str(e)}', 'danger')
            return redirect(url_for('admin.adhesion_form'))
    
    return render_template('admin/adhesion.html')


@admin_bp.route('/adhesion/confirmation/<int:adhesion_id>')
def adhesion_confirmation(adhesion_id):
    """Page de confirmation après soumission"""
    cursor, conn = execute_query("SELECT * FROM adhesions WHERE id = ?", (adhesion_id,))
    adhesion = cursor.fetchone()
    conn.close()
    
    if not adhesion:
        flash("Adhésion introuvable.", "danger")
        return redirect(url_for('admin.adhesion_form'))
    
    return render_template('admin/adhesion_confirmation.html', adhesion=adhesion)


@admin_bp.route('/admin/adhesions')
@login_required
@admin_required
def manage_adhesions():
    """Tableau de bord admin pour voir toutes les adhésions"""
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        cursor, conn = execute_query("SELECT * FROM adhesions ORDER BY created_at DESC", ())
    else:
        cursor, conn = execute_query("SELECT * FROM adhesions WHERE status = ? ORDER BY created_at DESC", (status_filter,))
    
    adhesions = cursor.fetchall()
    conn.close()
    
    stats = {
        'total': len(adhesions),
        'new': sum(1 for a in adhesions if a['status'] == 'new'),
        'contacted': sum(1 for a in adhesions if a['status'] == 'contacted'),
        'converted': sum(1 for a in adhesions if a['status'] == 'converted'),
        'rejected': sum(1 for a in adhesions if a['status'] == 'rejected')
    }
    
    return render_template('admin/adhesions_list.html', adhesions=adhesions, stats=stats, current_status=status_filter)


@admin_bp.route('/admin/adhesions/update_status/<int:adhesion_id>/<status>')
@login_required
@admin_required
def update_adhesion_status(adhesion_id, status):
    """Mettre à jour le statut d'une adhésion"""
    if status not in ['new', 'contacted', 'converted', 'rejected']:
        flash("Statut invalide.", "danger")
        return redirect(url_for('admin.manage_adhesions'))
    
    cursor, conn = execute_query("UPDATE adhesions SET status = ? WHERE id = ?", (status, adhesion_id))
    conn.commit()
    conn.close()
    
    flash(f"Statut mis à jour : {status}", "success")
    return redirect(url_for('admin.manage_adhesions'))


@admin_bp.route('/admin/adhesions/delete/<int:adhesion_id>')
@login_required
@admin_required
def delete_adhesion(adhesion_id):
    """Supprimer une adhésion"""
    cursor, conn = execute_query("DELETE FROM adhesions WHERE id = ?", (adhesion_id,))
    conn.commit()
    conn.close()
    flash("Adhésion supprimée.", "success")
    return redirect(url_for('admin.manage_adhesions'))