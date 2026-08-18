from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, SelectField, DateField, 
                     FloatField, TextAreaField, IntegerField, HiddenField)
from wtforms.validators import DataRequired, NumberRange, Optional, Length

class FeeForm(FlaskForm):
    level_id = SelectField('Niveau / Classe', coerce=int, validators=[DataRequired()])
    fee_type = SelectField('Type de frais', choices=[
        ('inscription', 'Frais d\'inscription'),
        ('scolarite', 'Frais de scolarité (Mensuel/Trimestriel)'),
        ('examen', 'Frais d\'examen'),
        ('autre', 'Autre')
    ], validators=[DataRequired()])
    amount = FloatField('Montant (FCFA)', validators=[DataRequired(), NumberRange(min=0)])
    due_date = DateField('Date limite de paiement', validators=[DataRequired()])
    submit = SubmitField('Enregistrer les frais')

class PaymentForm(FlaskForm):
    student_id = SelectField('Élève', coerce=int, validators=[DataRequired()])
    amount = FloatField('Montant payé (FCFA)', validators=[DataRequired(), NumberRange(min=0)])
    payment_date = DateField('Date du paiement', validators=[DataRequired()])
    payment_method = SelectField('Mode de paiement', choices=[
        ('especes', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement bancaire'),
        ('mobile_money', 'Mobile Money')
    ], validators=[DataRequired()])
    receipt_number = StringField('N° de Reçu (laisser vide pour auto)', validators=[])
    submit = SubmitField('Enregistrer le paiement')
    

class TeacherRateForm(FlaskForm):
    teacher_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    hourly_rate = FloatField('Taux horaire (FCFA)', validators=[DataRequired(), NumberRange(min=0)])
    effective_date = DateField('Date d\'effet', validators=[DataRequired()])
    submit = SubmitField('💾 Enregistrer le taux')

class TeachingHoursForm(FlaskForm):
    teacher_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Matière', coerce=int, validators=[DataRequired()])
    hours_count = FloatField('Nombre d\'heures', validators=[DataRequired(), NumberRange(min=0.5)])
    teaching_date = DateField('Date du cours', validators=[DataRequired()])
    comment = TextAreaField('Commentaire', validators=[Optional()])
    submit = SubmitField('💾 Enregistrer les heures')

class TeacherPaymentForm(FlaskForm):
    teacher_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    amount = FloatField('Montant payé (FCFA)', validators=[DataRequired(), NumberRange(min=0)])
    payment_date = DateField('Date de paiement', validators=[DataRequired()])
    payment_method = SelectField('Mode de paiement', choices=[
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('mobile', 'Mobile Money')
    ], validators=[DataRequired()])
    period_start = DateField('Période début', validators=[Optional()])
    period_end = DateField('Période fin', validators=[Optional()])
    comment = TextAreaField('Commentaire', validators=[Optional()])
    submit = SubmitField('💾 Enregistrer le paiement')

class ExpenseForm(FlaskForm):
    category = SelectField('Catégorie', choices=[
        ('fournitures', 'Fournitures scolaires'),
        ('electricite', 'Électricité'),
        ('eau', 'Eau'),
        ('internet', 'Internet/Téléphone'),
        ('loyer', 'Loyer'),
        ('transport', 'Transport'),
        ('maintenance', 'Maintenance/Réparations'),
        ('salaires', 'Salaires/Primes'),
        ('autre', 'Autre')
    ], validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired(), Length(max=200)])
    amount = FloatField('Montant (FCFA)', validators=[DataRequired(), NumberRange(min=0)])
    expense_date = DateField('Date de la dépense', validators=[DataRequired()])
    payment_method = SelectField('Mode de paiement', choices=[
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('mobile', 'Mobile Money')
    ], validators=[DataRequired()])
    submit = SubmitField('💾 Enregistrer la dépense')