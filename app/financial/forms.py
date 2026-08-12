from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, DateField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange

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