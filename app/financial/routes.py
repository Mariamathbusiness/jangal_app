import uuid
from datetime import datetime
from io import BytesIO
import pandas as pd

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, send_file
from flask_login import login_required, current_user
from app.financial.forms import FeeForm, PaymentForm
from app import get_db, execute_query)
from weasyprint import HTML

financial_bp = Blueprint('financial', __name__, template_folder='../templates/financial')

def get_current_academic_year(school_id=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor, conn = execute_query("SELECT id, label FROM academic_years WHERE school_id = ? AND is_current = 1 LIMIT 1", (school_id,,))
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
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    
    cursor, conn = execute_query("SELECT id, name FROM levels WHERE school_id = ?", (current_user.school_id or 1,,))
    form.level_id.choices = [(row['id'], row['name']) for row in cursor.fetchall()]
    
    if form.validate_on_submit():
        cursor.execute("""INSERT INTO fees (uuid, school_id, level_id, fee_type, amount, due_date, academic_year_id)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""", (
            str(uuid.uuid4()), current_user.school_id or 1, form.level_id.data, form.fee_type.data,
            form.amount.data, form.due_date.data.strftime('%Y-%m-%d'), current_year['id'] if current_year else 1
        ))
        conn.commit()
        flash('Frais enregistrés avec succès.', 'success')
        return redirect(url_for('financial.manage_fees'))
    
    cursor.execute("""SELECT f.id, f.fee_type, f.amount, f.due_date, l.name as level_name 
                      FROM fees f LEFT JOIN levels l ON f.level_id = l.id 
                      WHERE f.school_id = ? ORDER BY f.due_date DESC""", (current_user.school_id or 1,))
    fees = cursor.fetchall()
    conn.close()
    return render_template('financial/fees.html', form=form, fees=fees, current_year=current_year)

@financial_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def record_payment():
    form = PaymentForm()
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    
    if current_year:
        cursor.execute("""SELECT s.id, s.first_name, s.last_name, s.matricule 
                          FROM students s JOIN enrollments e ON s.id = e.student_id 
                          WHERE e.academic_year_id = ? AND e.status = 'active' ORDER BY s.last_name ASC""", (current_year['id'],))
    else:
        cursor.execute("SELECT id, first_name, last_name, matricule FROM students ORDER BY last_name ASC")
    
    form.student_id.choices = [(row['id'], f"{row['last_name']} {row['first_name']} ({row['matricule']})") for row in cursor.fetchall()]
    
    if form.validate_on_submit():
        receipt_num = form.receipt_number.data.strip() if form.receipt_number.data else f"REC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute("""INSERT INTO payments (uuid, student_id, amount, payment_date, payment_method, receipt_number, received_by)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""", (
            str(uuid.uuid4()), form.student_id.data, form.amount.data, 
            form.payment_date.data.strftime('%Y-%m-%d'), form.payment_method.data, receipt_num, current_user.id
        ))
        conn.commit()
        flash(f'Paiement enregistré. Reçu N° {receipt_num}', 'success')
        return redirect(url_for('financial.record_payment'))
    
    cursor.execute("""SELECT p.id, p.receipt_number, p.amount, p.payment_date, p.payment_method, 
                             s.first_name, s.last_name, s.matricule
                      FROM payments p JOIN students s ON p.student_id = s.id 
                      WHERE p.received_by = ? ORDER BY p.payment_date DESC LIMIT 20""", (current_user.id,))
    payments = cursor.fetchall()
    conn.close()
    return render_template('financial/payments.html', form=form, payments=payments)

@financial_bp.route('/receipt/<int:payment_id>')
@login_required
def generate_receipt(payment_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.receipt_number, p.amount, p.payment_date, p.payment_method,
               s.first_name, s.last_name, s.matricule, s.address,
               sch.name as school_name, sch.address as school_address, sch.phone as school_phone
        FROM payments p
        JOIN students s ON p.student_id = s.id
        JOIN schools sch ON s.school_id = sch.id
        WHERE p.id = ?
    """, (payment_id,))
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

# ============================================================
# SITUATION FINANCIÈRE PAR CLASSE
# ============================================================
@financial_bp.route('/financial_status')
@login_required
def financial_status():
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    
    selected_class_id = request.args.get('class_id', type=int)
    
    cursor.execute("SELECT id, label FROM classes ORDER BY label ASC")
    classes = cursor.fetchall()
    
    if selected_class_id:
        cursor.execute("""
            SELECT s.id, s.matricule, s.first_name, s.last_name, s.gender,
                   c.label as class_name, l.name as level_name, l.id as level_id
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id
            JOIN levels l ON c.level_id = l.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
            ORDER BY s.last_name ASC
        """, (selected_class_id, year_id))
    else:
        cursor.execute("""
            SELECT s.id, s.matricule, s.first_name, s.last_name, s.gender,
                   c.label as class_name, l.name as level_name, l.id as level_id
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id
            JOIN levels l ON c.level_id = l.id
            WHERE e.academic_year_id = ? AND e.status = 'active'
            ORDER BY c.label, s.last_name ASC
        """, (year_id,))
    
    students = cursor.fetchall()
    financial_data = []
    total_due = 0
    total_paid = 0
    total_balance = 0
    
    for student in students:
        student_id = student['id']
        level_id = student['level_id']
        
        cursor, conn = execute_query("SELECT COALESCE(SUM(amount), 0) as total_fees FROM fees WHERE level_id = ? AND academic_year_id = ?", (level_id, year_id,))
        fees_result = cursor.fetchone()
        amount_due = fees_result['total_fees'] if fees_result else 0
        
        cursor, conn = execute_query("SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE student_id = ?", (student_id,,))
        paid_result = cursor.fetchone()
        amount_paid = paid_result['total_paid'] if paid_result else 0
        
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
    conn = get_db()
    cursor = conn.cursor()
    current_year = get_current_academic_year(current_user.school_id or 1)
    year_id = current_year['id'] if current_year else None
    selected_class_id = request.args.get('class_id', type=int)
    
    if selected_class_id:
        cursor.execute("""
            SELECT s.id, s.matricule, s.first_name, s.last_name, c.label as class_name, l.id as level_id
            FROM students s JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id JOIN levels l ON c.level_id = l.id
            WHERE e.class_id = ? AND e.academic_year_id = ? AND e.status = 'active'
        """, (selected_class_id, year_id))
    else:
        cursor.execute("""
            SELECT s.id, s.matricule, s.first_name, s.last_name, c.label as class_name, l.id as level_id
            FROM students s JOIN enrollments e ON s.id = e.student_id
            JOIN classes c ON e.class_id = c.id JOIN levels l ON c.level_id = l.id
            WHERE e.academic_year_id = ? AND e.status = 'active'
        """, (year_id,))
    
    students = cursor.fetchall()
    data = []
    
    for student in students:
        cursor, conn = execute_query("SELECT COALESCE(SUM(amount), 0) FROM fees WHERE level_id = ? AND academic_year_id = ?", (student['level_id'], year_id,))
        amount_due = cursor.fetchone()[0]
        
        cursor, conn = execute_query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE student_id = ?", (student['id'],,))
        amount_paid = cursor.fetchone()[0]
        
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