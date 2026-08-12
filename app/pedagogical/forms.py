from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, StringField, SubmitField, DateField
from wtforms.validators import DataRequired, NumberRange, Length

# ============================================================
# FORMULAIRES DE SAISIE DES NOTES
# ============================================================
class GradeSelectionForm(FlaskForm):
    class_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Matière', coerce=int, validators=[DataRequired()])
    term = SelectField('Période', choices=[
        ('Trimestre 1', 'Trimestre 1'),
        ('Trimestre 2', 'Trimestre 2'),
        ('Trimestre 3', 'Trimestre 3'),
        ('Semestre 1', 'Semestre 1'),
        ('Semestre 2', 'Semestre 2'),
        ('Annuel', 'Annuel')
    ], validators=[DataRequired()])
    grade_type = SelectField('Type de note', choices=[
        ('CC', 'Contrôle Continu (CC)'),
        ('EXAMEN', 'Examen / Composition'),
        ('DEVOIR', 'Devoir'),
        ('INTERROGATION', 'Interrogation')
    ], validators=[DataRequired()])
    submit = SubmitField('Afficher la liste des élèves')


class GradeEntryForm(FlaskForm):
    grade_value = FloatField('Note / 20', validators=[DataRequired(), NumberRange(min=0, max=20)])
    coefficient = FloatField('Coefficient', default=1.0, validators=[DataRequired()])
    comment = StringField('Appréciation / Commentaire', validators=[Length(max=200)])


# ============================================================
# FORMULAIRES D'ABSENCES ET RETARDS
# ============================================================
class AttendanceForm(FlaskForm):
    class_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Afficher la liste')


# ============================================================
# FORMULAIRES D'EMPLOI DU TEMPS
# ============================================================
class ScheduleForm(FlaskForm):
    class_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Matière', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    day_of_week = SelectField('Jour', choices=[
        (1, 'Lundi'), (2, 'Mardi'), (3, 'Mercredi'), 
        (4, 'Jeudi'), (5, 'Vendredi'), (6, 'Samedi')
    ], coerce=int, validators=[DataRequired()])
    start_time = StringField('Heure début (ex: 08:00)', validators=[DataRequired()])
    end_time = StringField('Heure fin (ex: 10:00)', validators=[DataRequired()])
    room = StringField('Salle', validators=[Length(max=50)])
    submit = SubmitField('Ajouter au planning')