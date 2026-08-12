import uuid
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import login_required, current_user

from app.pedagogical.forms import GradeSelectionForm, AttendanceForm, ScheduleForm
from app import get_db
from weasyprint import HTML

pedagogical_bp = Blueprint('pedagogical', __name__, template_folder='../templates/pedagogical')


def get_current_academic_year(school_id=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, label FROM academic_years WHERE school_id = ? AND is_current = 1 LIMIT 1", (school_id,))
    year = cursor.fetchone()
    conn.close()
    return year


def calculate_grades(subjects_data):
    """Calcule les moyennes et points pour chaque matière"""
    total_points = 0.0
    total_coefficients = 0.0

    for row in subjects_data:
        cc = row['cc'] or 0.0
        examen = row['examen'] or 0.0
        coef = row['coefficient'] or 1.0

        note_count = (1 if row['cc'] is not None else 0) + (1 if row['examen'] is not None else 0)
        if note_count > 0:
            moyenne = ((cc if row['cc'] is not None else 0) + (examen if row['examen'] is not None else 0)) / note_count
        else:
            moyenne = 0.0

        row['moyenne'] = round(moyenne, 2)
        row['points'] = round(moyenne * coef, 2)

        total_points += row['points']
        total_coefficients += coef

    return total_points, total_coefficients, subjects_data


# ============================================================
# DASHBOARD
# ============================================================
@pedagogical_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('pedagogical/dashboard.html')


# ============================================================
# SAISIE DES NOTES (AVEC TRIMESTRE)
# ============================================================
@pedagogical_bp.route('/grades/enter', methods=['GET', 'POST'])
@login_required
def enter_grades():
    form = GradeSelectionForm()
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    # Peupler les classes
    cursor.execute("SELECT id, label FROM classes ORDER BY label ASC")
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]
    
    # Peupler les matières (filtrées par enseignant si c'est un prof)
    if current_user.role == 'teacher':
        cursor.execute("""
            SELECT sub.id, sub.name FROM subjects sub
            JOIN teacher_subjects ts ON sub.id = ts.subject_id
            WHERE ts.teacher_id = ?
            ORDER BY sub.name ASC
        """, (current_user.id,))
    else:
        cursor.execute("SELECT id, name FROM subjects ORDER BY name ASC")
    form.subject_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    
    students_data = []
    selected_class_id = None
    selected_subject_id = None
    selected_term = None
    
    if form.validate_on_submit():
        selected_class_id = form.class_id.data
        selected_subject_id = form.subject_id.data
        selected_term = form.term.data
        
        # Récupérer les élèves de la classe
        cursor.execute("""
            SELECT e.id as enrollment_id, s.id as student_id, s.first_name, s.last_name, s.matricule
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
            ORDER BY s.last_name ASC
        """, (selected_class_id, year_id))
        students = cursor.fetchall()
        
        # Récupérer les notes existantes pour ce trimestre
        cursor.execute("""
            SELECT enrollment_id, grade_value, coefficient, comment
            FROM grades
            WHERE subject_id = ? AND term = ?
        """, (selected_subject_id, selected_term))
        existing_grades = {row['enrollment_id']: row for row in cursor.fetchall()}
        
        for student in students:
            student_dict = dict(student)
            if student['enrollment_id'] in existing_grades:
                student_dict['grade_value'] = existing_grades[student['enrollment_id']]['grade_value']
                student_dict['coefficient'] = existing_grades[student['enrollment_id']]['coefficient']
                student_dict['comment'] = existing_grades[student['enrollment_id']]['comment']
            else:
                student_dict['grade_value'] = ''
                student_dict['coefficient'] = 1.0
                student_dict['comment'] = ''
            students_data.append(student_dict)
    
    conn.close()
    return render_template('pedagogical/enter_grades.html', form=form, students=students_data,
                          selected_class_id=selected_class_id, selected_subject_id=selected_subject_id,
                          selected_term=selected_term)


@pedagogical_bp.route('/grades/save', methods=['POST'])
@login_required
def save_grades():
    conn = get_db()
    cursor = conn.cursor()
    
    subject_id = request.form.get('subject_id', type=int)
    term = request.form.get('term')
    # On récupère le type de note depuis le champ caché (que nous allons renommer)
    grade_type = request.form.get('type_note', 'CC') 
    
    for key, value in request.form.items():
        if key.startswith('grade_'):
            parts = key.split('_')
            # On vérifie que la deuxième partie est bien un chiffre (ex: 'grade_12' -> '12')
            if len(parts) == 2 and parts[1].isdigit():
                enrollment_id = int(parts[1])
                try:
                    grade_value = float(value) if value else None
                    coefficient = float(request.form.get(f'coef_{enrollment_id}', 1.0))
                    comment = request.form.get(f'comment_{enrollment_id}', '')
                    
                    if grade_value is not None:
                        cursor.execute("""
                            SELECT id FROM grades 
                            WHERE enrollment_id = ? AND subject_id = ? AND term = ?
                        """, (enrollment_id, subject_id, term))
                        existing = cursor.fetchone()
                        
                        if existing:
                            cursor.execute("""
                                UPDATE grades SET grade_value = ?, coefficient = ?, comment = ?, grade_type = ?
                                WHERE id = ?
                            """, (grade_value, coefficient, comment, grade_type, existing['id']))
                        else:
                            cursor.execute("""
                                INSERT INTO grades (uuid, enrollment_id, subject_id, grade_value, coefficient, grade_type, term, comment, entered_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (str(uuid.uuid4()), enrollment_id, subject_id, grade_value, coefficient, 
                                  grade_type, term, comment, current_user.id))
                except ValueError:
                    continue
    
    conn.commit()
    conn.close()
    flash('Notes enregistrées avec succès !', 'success')
    return redirect(url_for('pedagogical.enter_grades'))


# ============================================================
# GÉNÉRATION DES BULLETINS PDF
# ============================================================
@pedagogical_bp.route('/bulletin/<int:student_id>')
@login_required
def generate_bulletin(student_id):
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None

    if not year_id:
        flash("Aucune année scolaire en cours définie.", "danger")
        return redirect(url_for('pedagogical.dashboard'))

    # 1. Récupérer les infos de l'élève
    cursor.execute("""
        SELECT s.first_name, s.last_name, s.matricule, s.gender, s.photo_path,
               c.label as class_name, l.name as level_name, l.level_type,
               sch.name as school_name, sch.address as school_address
        FROM students s
        JOIN enrollments e ON s.id = e.student_id
        JOIN classes c ON e.class_id = c.id
        JOIN levels l ON c.level_id = l.id
        JOIN schools sch ON s.school_id = sch.id
        WHERE s.id = ? AND e.academic_year_id = ? AND e.status = 'active'
    """, (student_id, year_id))
    student_info = cursor.fetchone()

    if not student_info:
        flash("Élève non trouvé ou non inscrit cette année.", "danger")
        conn.close()
        return redirect(url_for('admin.manage_students'))

    # 2. Récupérer les matières et notes
    cursor.execute("""
        SELECT sub.name as subject_name, sub.code, sub.coefficient,
               MAX(CASE WHEN g.grade_type = 'CC' THEN g.grade_value END) as cc,
               MAX(CASE WHEN g.grade_type = 'EXAMEN' THEN g.grade_value END) as examen,
               g.comment
        FROM subjects sub
        LEFT JOIN grades g ON sub.id = g.subject_id AND g.enrollment_id = (
            SELECT id FROM enrollments WHERE student_id = ? AND academic_year_id = ?
        )
        GROUP BY sub.id
        ORDER BY sub.name ASC
    """, (student_id, year_id))

    subjects_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # 3. Aiguillage selon le niveau
    level_type = student_info['level_type']

    if level_type == 'preschool':
        template_name = 'pedagogical/bulletins/preschool.html'
        context = {
            'student': student_info,
            'subjects': subjects_data,
            'current_year': current_year
        }

    elif level_type == 'primary':
        template_name = 'pedagogical/bulletins/primary.html'
        total_points, total_coefficients, subjects_data = calculate_grades(subjects_data)
        general_average = round(total_points / total_coefficients, 2) if total_coefficients > 0 else 0.0
        context = {
            'student': student_info,
            'subjects': subjects_data,
            'general_average': general_average,
            'total_coefficients': total_coefficients,
            'rank': "N/A",
            'decision': "ADMIS(E)" if general_average >= 10.0 else "AJOURNÉ(E)",
            'appreciation': "Travail sérieux" if general_average >= 14 else "Doit faire des efforts",
            'current_year': current_year
        }

    elif level_type in ['middle', 'secondary']:
        template_name = 'pedagogical/bulletins/secondary.html'
        total_points, total_coefficients, subjects_data = calculate_grades(subjects_data)
        general_average = round(total_points / total_coefficients, 2) if total_coefficients > 0 else 0.0
        context = {
            'student': student_info,
            'subjects': subjects_data,
            'general_average': general_average,
            'total_coefficients': total_coefficients,
            'rank': "N/A",
            'decision': "ADMIS(E)" if general_average >= 10.0 else "AJOURNÉ(E)",
            'appreciation': "Travail sérieux" if general_average >= 14 else "Doit faire des efforts",
            'current_year': current_year
        }

    elif level_type == 'higher_edu':
        template_name = 'pedagogical/bulletins/higher_edu.html'
        total_points, total_coefficients, subjects_data = calculate_grades(subjects_data)
        general_average = round(total_points / total_coefficients, 2) if total_coefficients > 0 else 0.0
        context = {
            'student': student_info,
            'subjects': subjects_data,
            'general_average': general_average,
            'total_coefficients': total_coefficients,
            'rank': "N/A",
            'decision': "VALIDÉ" if general_average >= 10.0 else "NON VALIDÉ",
            'appreciation': "Parcours validé" if general_average >= 14 else "Parcours en cours",
            'current_year': current_year
        }

    else:
        flash("Type de niveau non reconnu.", "danger")
        return redirect(url_for('admin.manage_students'))

    # 4. Génération du PDF via WeasyPrint
    html_content = render_template(template_name, **context)
    pdf_file = HTML(string=html_content).write_pdf()

    return Response(
        pdf_file,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment; filename=Bulletin_{student_info['last_name']}_{student_info['first_name']}.pdf"}
    )


# ============================================================
# ABSENCES ET RETARDS
# ============================================================
@pedagogical_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
def take_attendance():
    form = AttendanceForm()
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None

    cursor.execute("SELECT id, label FROM classes ORDER BY label ASC")
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]

    students_data = []
    if form.validate_on_submit():
        class_id = form.class_id.data
        att_date = form.date.data.strftime('%Y-%m-%d')

        # Récupérer les élèves de la classe
        cursor.execute("""
            SELECT e.id as enrollment_id, s.id as student_id, s.first_name, s.last_name
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
            ORDER BY s.last_name ASC
        """, (class_id, year_id))
        students = cursor.fetchall()

        # Récupérer les absences existantes pour cette date
        cursor.execute("""
            SELECT enrollment_id, status, comment FROM attendances WHERE date = ?
        """, (att_date,))
        existing_attendance = {row['enrollment_id']: row for row in cursor.fetchall()}

        for student in students:
            student_dict = dict(student)
            if student['enrollment_id'] in existing_attendance:
                student_dict['status'] = existing_attendance[student['enrollment_id']]['status']
                student_dict['comment'] = existing_attendance[student['enrollment_id']]['comment']
            else:
                student_dict['status'] = 'present'
                student_dict['comment'] = ''
            students_data.append(student_dict)

    conn.close()
    return render_template('pedagogical/attendance.html', form=form, students=students_data, att_date=form.date.data if form.date.data else None)

@pedagogical_bp.route('/attendance/save', methods=['POST'])
@login_required
def save_attendance():
    conn = get_db()
    cursor = conn.cursor()
    att_date = request.form.get('date')
    class_id = request.form.get('class_id')

    for key, value in request.form.items():
        if key.startswith('status_'):
            enrollment_id = int(key.split('_')[1])
            status = value
            comment = request.form.get(f'comment_{enrollment_id}', '')

            cursor.execute("SELECT id FROM attendances WHERE enrollment_id = ? AND date = ?", (enrollment_id, att_date))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("UPDATE attendances SET status = ?, comment = ?, marked_by = ? WHERE id = ?", 
                               (status, comment, current_user.id, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO attendances (uuid, enrollment_id, date, status, marked_by, comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), enrollment_id, att_date, status, current_user.id, comment))

    conn.commit()
    conn.close()
    flash('Présence enregistrée avec succès !', 'success')
    return redirect(url_for('pedagogical.take_attendance'))


# ============================================================
# EMPLOI DU TEMPS
# ============================================================
@pedagogical_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
def manage_schedule():
    form = ScheduleForm()
    conn = get_db()
    cursor = conn.cursor()

    # 1. Peupler les choix des classes
    cursor.execute("SELECT id, label FROM classes ORDER BY label ASC")
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]
    
    # 2. Peupler les choix des matières
    cursor.execute("SELECT id, name FROM subjects ORDER BY name ASC")
    form.subject_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    
    # 3. Peupler les choix des enseignants avec leurs matières
    cursor.execute("""
        SELECT u.id, u.full_name, u.username,
               GROUP_CONCAT(sub.name, ', ') as subjects
        FROM users u
        LEFT JOIN teacher_subjects ts ON u.id = ts.teacher_id
        LEFT JOIN subjects sub ON ts.subject_id = sub.id
        WHERE u.role = 'teacher'
        GROUP BY u.id
        ORDER BY u.full_name ASC
    """)
    
    teacher_choices = []
    for row in cursor.fetchall():
        name = row['full_name'] or row['username']
        subjects = row['subjects']
        if subjects:
            label = f"{name} ({subjects})"
        else:
            label = f"{name} (Aucune matière assignée)"
        teacher_choices.append((row['id'], label))
    
    form.teacher_id.choices = teacher_choices

    # 4. Traitement du formulaire soumis
    if form.validate_on_submit():
        cursor.execute("""
            INSERT INTO schedules (uuid, class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), form.class_id.data, form.subject_id.data, form.teacher_id.data,
            form.day_of_week.data, form.start_time.data, form.end_time.data, form.room.data
        ))
        conn.commit()
        flash('Créneau ajouté à l\'emploi du temps.', 'success')
        conn.close()
        return redirect(url_for('pedagogical.manage_schedule'))

    # 5. Récupérer l'emploi du temps pour l'affichage
    cursor.execute("""
        SELECT s.id, s.day_of_week, s.start_time, s.end_time, s.room,
               c.label as class_name, sub.name as subject_name, u.full_name as teacher_name
        FROM schedules s
        JOIN classes c ON s.class_id = c.id
        JOIN subjects sub ON s.subject_id = sub.id
        LEFT JOIN users u ON s.teacher_id = u.id
        ORDER BY s.day_of_week, s.start_time
    """)
    schedule_items = cursor.fetchall()
    conn.close()

    return render_template('pedagogical/schedule.html', form=form, schedule_items=schedule_items)

@pedagogical_bp.route('/schedule/delete/<int:schedule_id>')
@login_required
def delete_schedule(schedule_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    flash('Créneau supprimé.', 'success')
    return redirect(url_for('pedagogical.manage_schedule'))