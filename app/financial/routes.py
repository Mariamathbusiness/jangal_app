import uuid
from datetime import datetime, date
from io import BytesIO
import pandas as pd

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, send_file
from flask_login import login_required, current_user
from app.financial.forms import FeeForm, PaymentForm, TeacherRateForm, TeachingHoursForm, TeacherPaymentForm, ExpenseForm
from app import get_db, execute_query
from weasyprint import HTML

financial_bp = Blueprint('financial', __name__, template_folder='../templates/financial')

def get_current_academic_year(school_id=1):
    query = "SELECT id, label FROM academic_years WHERE school_id = ? AND is_current = 1 LIMIT 1"
    cursor, conn = execute_query(query, (school_id,))
    year = cursor.fetchone()
    conn.close()
    return year

@financial_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('financial/dashboard.html')

@financial_bp.route('/fees', methods=['GET', 'POST'])
@login_required
def manage_fees():
    form = FeeForm()
    current_year = get_current_academic_year(current_user.school_id or 1)
    
    query = "SELECT id, name FROM levels WHERE school_id = ?"
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    form.level_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        query = """INSERT INTO fees (uuid, school_id, level_id, fee_type, amount, due_date, academic_year_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), current_user.school_id or 1, form.level_id.data, form.fee_type.data,
            form.amount.data, form.due_date.data.strftime('%Y-%m-%d'), current_year['id'] if current_year else 1
        ))
        conn.commit()
        conn.close()
        flash('Frais enregistrés avec succès.', 'success')
        return redirect(url_for('financial.manage_fees'))
    
    query = """SELECT f.id, f.fee_type, f.amount, f.due_date, l.name as level_name 
               FROM fees f LEFT JOIN levels l ON f.level_id = l.id 
               WHERE f.school_id = ? ORDER BY f.due_date DESC"""
    cursor, conn = execute_query(query, (current_user.school_id or 1,))
    fees = cursor.fetchall()
    conn.close()
    
    return render_template('financial/fees.html', form=form, fees=fees, current_year=current_year)

@financial_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def record_payment():
    form = PaymentForm()
    current_year = get_current_academic_year(current_user.school_id or 1)
    
    if current_year:
        query = """SELECT s.id, s.first_name, s.last_name, s.matricule 
                   FROM students s JOIN enrollments e ON s.id = e.student_id 
                   WHERE e.academic_year_id = ? AND e.status = 'active' ORDER BY s.last_name ASC"""
        cursor, conn = execute_query(query, (current_year['id'],))
    else:
        cursor, conn = execute_query("SELECT id, first_name, last_name, matricule FROM students ORDER BY last_name ASC", ())
    
    form.student_id.choices = [(row['id'], f"{row['last_name']} {row['first_name']} ({row['matricule']})") for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        receipt_num = form.receipt_number.data.strip() if form.receipt_number.data else f"REC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        query = """INSERT INTO payments (uuid, student_id, amount, payment_date, payment_method, receipt_number, received_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), form.student_id.data, form.amount.data, 
            form.payment_date.data.strftime('%Y-%m-%d'), form.payment_method.data, receipt_num, current_user.id
        ))
        conn.commit()
        conn.close()
        flash(f'Paiement enregistré. Reçu N° {receipt_num}', 'success')
        return redirect(url_for('financial.record_payment'))
    
    query = """SELECT p.id, p.receipt_number, p.amount, p.payment_date, p.payment_method, 
                      s.first_name, s.last_name, s.matricule
               FROM payments p JOIN students s ON p.student_id = s.id 
               WHERE p.received_by = ? ORDER BY p.payment_date DESC LIMIT 20"""
    cursor, conn = execute_query(query, (current_user.id,))
    payments = cursor.fetchall()
    conn.close()
    
    return render_template('financial/payments.html', form=form, payments=payments)

@financial_bp.route('/receipt/<int:payment_id>')
@login_required
def generate_receipt(payment_id):
    query = """SELECT p.receipt_number, p.amount, p.payment_date, p.payment_method,
               s.first_name, s.last_name, s.matricule, s.address,
               sch.name as school_name, sch.address as school_address, sch.phone as school_phone
        FROM payments p
        JOIN students s ON p.student_id = s.id
        JOIN schools sch ON s.school_id = sch.id
        WHERE p.id = ?"""
    cursor, conn = execute_query(query, (payment_id,))
    payment_info = cursor.fetchone()
    conn.close()
    
    if not payment_info:
        flash("Reçu introuvable.", "danger")
        return redirect(url_for('financial.record_payment'))

    html_content = render_template('financial/receipt.html', payment=payment_info)
    pdf_file = HTML(string=html_content).write_pdf()

    return Response(
        pdf_file,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment; filename=Recu_{payment_info['receipt_number']}.pdf"}
    )

@financial_bp.route('/financial_status')
@login_required
def financial_status():
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    selected_class_id = request.args.get('class_id', type=int)
    
    cursor, conn = execute_query("SELECT id, label FROM classes ORDER BY label ASC", ())
    classes = cursor.fetchall()
    
    if selected_class_id:
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name, s.gender,
                   c.label as class_name, l.name as level_name, l.id as level_id
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id
            JOIN levels l ON c.level_id = l.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
            ORDER BY s.last_name ASC"""
        cursor, conn = execute_query(query, (selected_class_id, year_id))
    else:
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name, s.gender,
                   c.label as class_name, l.name as level_name, l.id as level_id
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id
            JOIN levels l ON c.level_id = l.id
            WHERE e.academic_year_id = ? AND e.status = 'active'
            ORDER BY c.label, s.last_name ASC"""
        cursor, conn = execute_query(query, (year_id,))
    
    students = cursor.fetchall()
    financial_data = []
    total_due = 0
    total_paid = 0
    total_balance = 0
    
    for student in students:
        student_id = student['id']
        level_id = student['level_id']
        
        query_fees = "SELECT COALESCE(SUM(amount), 0) as total_fees FROM fees WHERE level_id = ? AND academic_year_id = ?"
        cursor_fees, conn_fees = execute_query(query_fees, (level_id, year_id))
        fees_result = cursor_fees.fetchone()
        amount_due = fees_result['total_fees'] if fees_result else 0
        conn_fees.close()
        
        query_paid = "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE student_id = ?"
        cursor_paid, conn_paid = execute_query(query_paid, (student_id,))
        paid_result = cursor_paid.fetchone()
        amount_paid = paid_result['total_paid'] if paid_result else 0
        conn_paid.close()
        
        balance = amount_paid - amount_due
        
        if amount_due == 0:
            status, status_label, status_color = 'no_fees', 'Non défini', 'secondary'
        elif balance >= 0:
            status, status_label, status_color = 'up_to_date', '✅ À jour', 'success'
        elif balance >= -amount_due * 0.5:
            status, status_label, status_color = 'partial', '⚠️ Partiel', 'warning'
        else:
            status, status_label, status_color = 'overdue', '❌ En retard', 'danger'
        
        financial_data.append({
            'student_id': student_id, 'matricule': student['matricule'],
            'full_name': f"{student['last_name']} {student['first_name']}",
            'class_name': student['class_name'], 'gender': student['gender'],
            'amount_due': amount_due, 'amount_paid': amount_paid, 'balance': balance,
            'status': status, 'status_label': status_label, 'status_color': status_color
        })
        
        total_due += amount_due
        total_paid += amount_paid
        total_balance += balance
    
    conn.close()
    
    stats = {
        'total_students': len(financial_data),
        'up_to_date': sum(1 for s in financial_data if s['status'] == 'up_to_date'),
        'partial': sum(1 for s in financial_data if s['status'] == 'partial'),
        'overdue': sum(1 for s in financial_data if s['status'] == 'overdue'),
        'total_due': total_due, 'total_paid': total_paid, 'total_balance': total_balance
    }
    
    return render_template('financial/financial_status.html', 
                          financial_data=financial_data, classes=classes,
                          selected_class_id=selected_class_id, stats=stats, current_year=current_year)

@financial_bp.route('/financial_status/export')
@login_required
def export_financial_status():
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    selected_class_id = request.args.get('class_id', type=int)
    
    if selected_class_id:
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name, c.label as class_name, l.id as level_id
            FROM students s JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id JOIN levels l ON c.level_id = l.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'"""
        cursor, conn = execute_query(query, (selected_class_id, year_id))
    else:
        query = """SELECT s.id, s.matricule, s.first_name, s.last_name, c.label as class_name, l.id as level_id
            FROM students s JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id JOIN levels l ON c.level_id = l.id
            WHERE e.academic_year_id = ? AND e.status = 'active'"""
        cursor, conn = execute_query(query, (year_id,))
    
    students = cursor.fetchall()
    data = []
    
    for student in students:
        query_fees = "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE level_id = ? AND academic_year_id = ?"
        cursor_fees, conn_fees = execute_query(query_fees, (student['level_id'], year_id))
        amount_due = cursor_fees.fetchone()[0]
        conn_fees.close()
        
        query_paid = "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE student_id = ?"
        cursor_paid, conn_paid = execute_query(query_paid, (student['id'],))
        amount_paid = cursor_paid.fetchone()[0]
        conn_paid.close()
        
        balance = amount_paid - amount_due
        status_text = 'À jour' if balance >= 0 else ('En retard' if balance < -amount_due * 0.5 else 'Partiel')
        
        data.append({
            'Matricule': student['matricule'], 'Nom': student['last_name'],
            'Prénom': student['first_name'], 'Classe': student['class_name'],
            'Montant Dû (FCFA)': amount_due, 'Montant Payé (FCFA)': amount_paid,
            'Solde (FCFA)': balance, 'Statut': status_text
        })
    
    conn.close()
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Situation Financière')
    output.seek(0)
    
    class_name = f"_Classe_{selected_class_id}" if selected_class_id else "_Toutes_Classes"
    filename = f"Situation_Financiere{class_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# ============================================================
# GESTION FINANCIÈRE AMÉLIORÉE (Taux, Heures, Paiements, Dépenses)
# ============================================================

@financial_bp.route('/financial/teacher_rates', methods=['GET', 'POST'])
@login_required
def manage_teacher_rates():
    form = TeacherRateForm()
    school_id = current_user.school_id or 1
    
    cursor, conn = execute_query(
        "SELECT id, full_name FROM users WHERE role = 'teacher' AND school_id = ? ORDER BY full_name",
        (school_id,)
    )
    form.teacher_id.choices = [(row['id'], row['full_name']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        query = """INSERT INTO teacher_rates (uuid, teacher_id, school_id, hourly_rate, effective_date)
                   VALUES (?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), form.teacher_id.data, school_id,
            form.hourly_rate.data, form.effective_date.data
        ))
        conn.commit()
        conn.close()
        flash('✅ Taux horaire enregistré avec succès.', 'success')
        return redirect(url_for('financial.manage_teacher_rates'))
    
    query = """SELECT tr.id, tr.hourly_rate, tr.effective_date, u.full_name as teacher_name
               FROM teacher_rates tr
               JOIN users u ON tr.teacher_id = u.id
               WHERE tr.school_id = ?
               ORDER BY u.full_name, tr.effective_date DESC"""
    cursor, conn = execute_query(query, (school_id,))
    rates = cursor.fetchall()
    conn.close()
    
    return render_template('financial/teacher_rates.html', form=form, rates=rates)


@financial_bp.route('/financial/teaching_hours', methods=['GET', 'POST'])
@login_required
def manage_teaching_hours():
    form = TeachingHoursForm()
    school_id = current_user.school_id or 1
    
    cursor, conn = execute_query(
        "SELECT id, full_name FROM users WHERE role = 'teacher' AND school_id = ? ORDER BY full_name",
        (school_id,)
    )
    form.teacher_id.choices = [(row['id'], row['full_name']) for row in cursor.fetchall()]
    
    cursor, conn = execute_query("SELECT id, label FROM classes ORDER BY label", ())
    form.class_id.choices = [(row['id'], row['label']) for row in cursor.fetchall()]
    
    cursor, conn = execute_query("SELECT id, name FROM subjects ORDER BY name", ())
    form.subject_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        current_year = get_current_academic_year(school_id)
        year_id = current_year['id'] if current_year else None
        
        query = """INSERT INTO teaching_hours 
                   (uuid, teacher_id, school_id, class_id, subject_id, hours_count, teaching_date, academic_year_id, comment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), form.teacher_id.data, school_id,
            form.class_id.data, form.subject_id.data, form.hours_count.data,
            form.teaching_date.data, year_id, form.comment.data
        ))
        conn.commit()
        conn.close()
        flash('✅ Heures enseignées enregistrées.', 'success')
        return redirect(url_for('financial.manage_teaching_hours'))
    
    query = """SELECT th.id, th.hours_count, th.teaching_date, th.comment,
                      u.full_name as teacher_name, c.label as class_name, sub.name as subject_name
               FROM teaching_hours th
               JOIN users u ON th.teacher_id = u.id
               LEFT JOIN classes c ON th.class_id = c.id
               LEFT JOIN subjects sub ON th.subject_id = sub.id
               WHERE th.school_id = ?
               ORDER BY th.teaching_date DESC LIMIT 50"""
    cursor, conn = execute_query(query, (school_id,))
    hours_list = cursor.fetchall()
    conn.close()
    
    return render_template('financial/teaching_hours.html', form=form, hours_list=hours_list)


@financial_bp.route('/financial/teacher_payments', methods=['GET', 'POST'])
@login_required
def manage_teacher_payments():
    form = TeacherPaymentForm()
    school_id = current_user.school_id or 1
    
    cursor, conn = execute_query(
        "SELECT id, full_name FROM users WHERE role = 'teacher' AND school_id = ? ORDER BY full_name",
        (school_id,)
    )
    form.teacher_id.choices = [(row['id'], row['full_name']) for row in cursor.fetchall()]
    conn.close()
    
    if form.validate_on_submit():
        query = """INSERT INTO teacher_payments 
                   (uuid, teacher_id, school_id, amount, payment_date, payment_method, 
                    period_start, period_end, comment, received_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), form.teacher_id.data, school_id,
            form.amount.data, form.payment_date.data, form.payment_method.data,
            form.period_start.data, form.period_end.data, form.comment.data, current_user.id
        ))
        conn.commit()
        conn.close()
        flash('✅ Paiement enregistré.', 'success')
        return redirect(url_for('financial.manage_teacher_payments'))
    
    query_teachers = """SELECT id, full_name FROM users 
                        WHERE role = 'teacher' AND school_id = ? ORDER BY full_name"""
    cursor, conn = execute_query(query_teachers, (school_id,))
    teachers = cursor.fetchall()
    
    teachers_balance = []
    for teacher in teachers:
        cursor_rate, conn_rate = execute_query(
            """SELECT hourly_rate FROM teacher_rates 
               WHERE teacher_id = ? AND school_id = ? 
               ORDER BY effective_date DESC LIMIT 1""",
            (teacher['id'], school_id)
        )
        rate_row = cursor_rate.fetchone()
        hourly_rate = rate_row['hourly_rate'] if rate_row else 0
        conn_rate.close()
        
        cursor_hours, conn_hours = execute_query(
            """SELECT COALESCE(SUM(hours_count), 0) as total_hours 
               FROM teaching_hours WHERE teacher_id = ? AND school_id = ?""",
            (teacher['id'], school_id)
        )
        total_hours = cursor_hours.fetchone()['total_hours']
        conn_hours.close()
        
        cursor_paid, conn_paid = execute_query(
            """SELECT COALESCE(SUM(amount), 0) as total_paid 
               FROM teacher_payments WHERE teacher_id = ? AND school_id = ?""",
            (teacher['id'], school_id)
        )
        total_paid = cursor_paid.fetchone()['total_paid']
        conn_paid.close()
        
        amount_due = (total_hours * hourly_rate) - total_paid
        
        teachers_balance.append({
            'teacher_id': teacher['id'],
            'teacher_name': teacher['full_name'],
            'hourly_rate': hourly_rate,
            'total_hours': total_hours,
            'total_earned': total_hours * hourly_rate,
            'total_paid': total_paid,
            'balance': amount_due
        })
    
    cursor, conn = execute_query(
        """SELECT tp.id, tp.amount, tp.payment_date, tp.payment_method, tp.comment,
                  u.full_name as teacher_name
           FROM teacher_payments tp
           JOIN users u ON tp.teacher_id = u.id
           WHERE tp.school_id = ?
           ORDER BY tp.payment_date DESC LIMIT 30""",
        (school_id,)
    )
    payments_history = cursor.fetchall()
    conn.close()
    
    return render_template('financial/teacher_payments.html', 
                          form=form, 
                          teachers_balance=teachers_balance,
                          payments_history=payments_history)


@financial_bp.route('/financial/expenses', methods=['GET', 'POST'])
@login_required
def manage_expenses():
    form = ExpenseForm()
    school_id = current_user.school_id or 1
    
    if form.validate_on_submit():
        query = """INSERT INTO expenses 
                   (uuid, school_id, category, description, amount, expense_date, payment_method, approved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor, conn = execute_query(query, (
            str(uuid.uuid4()), school_id, form.category.data,
            form.description.data, form.amount.data, form.expense_date.data,
            form.payment_method.data, current_user.id
        ))
        conn.commit()
        conn.close()
        flash('✅ Dépense enregistrée.', 'success')
        return redirect(url_for('financial.manage_expenses'))
    
    cursor_in, conn_in = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE school_id = ?",
        (school_id,)
    )
    total_income = cursor_in.fetchone()['total']
    conn_in.close()
    
    cursor_teach, conn_teach = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM teacher_payments WHERE school_id = ?",
        (school_id,)
    )
    total_teacher_payments = cursor_teach.fetchone()['total']
    conn_teach.close()
    
    cursor_exp, conn_exp = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE school_id = ?",
        (school_id,)
    )
    total_expenses = cursor_exp.fetchone()['total']
    conn_exp.close()
    
    cash_balance = total_income - total_teacher_payments - total_expenses
    
    cursor, conn = execute_query(
        """SELECT id, category, description, amount, expense_date, payment_method
           FROM expenses WHERE school_id = ?
           ORDER BY expense_date DESC LIMIT 50""",
        (school_id,)
    )
    expenses_list = cursor.fetchall()
    conn.close()
    
    return render_template('financial/expenses.html', 
                          form=form, 
                          expenses_list=expenses_list,
                          cash_balance=cash_balance,
                          total_income=total_income,
                          total_teacher_payments=total_teacher_payments,
                          total_expenses=total_expenses)


@financial_bp.route('/financial/closing_report')
@login_required
def closing_report():
    school_id = current_user.school_id or 1
    
    cursor, conn = execute_query("SELECT * FROM schools WHERE id = ?", (school_id,))
    school = cursor.fetchone()
    conn.close()
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    cursor, conn = execute_query(
        """SELECT COALESCE(SUM(amount), 0) as total 
           FROM payments WHERE school_id = ? AND payment_date BETWEEN ? AND ?""",
        (school_id, start_date, end_date)
    )
    period_income = cursor.fetchone()['total']
    conn.close()
    
    cursor, conn = execute_query(
        """SELECT COALESCE(SUM(amount), 0) as total 
           FROM teacher_payments WHERE school_id = ? AND payment_date BETWEEN ? AND ?""",
        (school_id, start_date, end_date)
    )
    period_teacher_payments = cursor.fetchone()['total']
    conn.close()
    
    cursor, conn = execute_query(
        """SELECT category, COALESCE(SUM(amount), 0) as total 
           FROM expenses WHERE school_id = ? AND expense_date BETWEEN ? AND ?
           GROUP BY category ORDER BY total DESC""",
        (school_id, start_date, end_date)
    )
    expenses_by_category = cursor.fetchall()
    period_expenses = sum(row['total'] for row in expenses_by_category)
    conn.close()
    
    cursor, conn = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE school_id = ?",
        (school_id,)
    )
    global_income = cursor.fetchone()['total']
    conn.close()
    
    cursor, conn = execute_query(
        """SELECT COALESCE(SUM(amount), 0) as total 
           FROM teacher_payments WHERE school_id = ?""",
        (school_id,)
    )
    global_teacher_payments = cursor.fetchone()['total']
    conn.close()
    
    cursor, conn = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE school_id = ?",
        (school_id,)
    )
    global_expenses = cursor.fetchone()['total']
    conn.close()
    
    global_balance = global_income - global_teacher_payments - global_expenses
    
    context = {
        'school': school,
        'start_date': start_date,
        'end_date': end_date,
        'period_income': period_income,
        'period_teacher_payments': period_teacher_payments,
        'period_expenses': period_expenses,
        'expenses_by_category': expenses_by_category,
        'period_balance': period_income - period_teacher_payments - period_expenses,
        'global_balance': global_balance
    }
    
    if request.args.get('print') == '1':
        html_content = render_template('financial/closing_report.html', **context)
        pdf_file = HTML(string=html_content).write_pdf()
        return Response(
            pdf_file,
            mimetype='application/pdf',
            headers={"Content-Disposition": f"attachment; filename=Brouillard_Cloture_{start_date}_to_{end_date}.pdf"}
        )
    
    return render_template('financial/closing_report.html', **context)