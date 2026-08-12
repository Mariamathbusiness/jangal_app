from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, SelectField, DateField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Email, Optional

# ============================================================
# FORMULAIRES ADMINISTRATIFS
# ============================================================
class AcademicYearForm(FlaskForm):
    label = StringField('Libellé (ex: 2024-2025)', validators=[DataRequired(), Length(max=50)])
    start_date = DateField('Date de début', validators=[DataRequired()])
    end_date = DateField('Date de fin', validators=[DataRequired()])
    is_current = SelectField('Année en cours', choices=[(1, 'Oui'), (0, 'Non')], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')

class LevelForm(FlaskForm):
    name = StringField('Nom du niveau (ex: Primaire, Collège)', validators=[DataRequired(), Length(max=100)])
    level_type = SelectField('Type de niveau', choices=[
        ('preschool', 'Préscolaire'),
        ('primary', 'Primaire'),
        ('middle', 'Moyen'),
        ('secondary', 'Secondaire'),
        ('higher_edu', 'Supérieur')
    ], validators=[DataRequired()])
    submit = SubmitField('Enregistrer')

class ClassForm(FlaskForm):
    label = StringField('Nom de la classe (ex: 6ème A)', validators=[DataRequired(), Length(max=100)])
    level_id = SelectField('Niveau', coerce=int, validators=[DataRequired()])
    room = StringField('Salle', validators=[Length(max=50)])
    capacity = FloatField('Capacité maximale', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Enregistrer')

class SubjectForm(FlaskForm):
    name = StringField('Nom de la matière', validators=[DataRequired(), Length(max=100)])
    code = StringField('Code (ex: MATH)', validators=[DataRequired(), Length(max=20)])
    coefficient = FloatField('Coefficient', validators=[DataRequired(), NumberRange(min=0.5)])
    credits = FloatField('Crédits (pour le supérieur, sinon 0)', validators=[NumberRange(min=0)])
    is_ue = SelectField('Est une Unité d\'Enseignement (UE) ?', choices=[(1, 'Oui'), (0, 'Non')], coerce=int)
    submit = SubmitField('Enregistrer')

class StudentForm(FlaskForm):
    matricule = StringField('Matricule (laisser vide pour génération auto)', validators=[Length(max=50)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=100)])
    date_of_birth = DateField('Date de naissance', validators=[DataRequired()])
    gender = SelectField('Genre', choices=[('M', 'Masculin'), ('F', 'Féminin')], validators=[DataRequired()])
    class_id = SelectField('Classe d\'inscription', coerce=int, validators=[DataRequired()])
    photo = FileField('Photo de l\'élève', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    submit = SubmitField('Inscrire l\'élève')

# ============================================================
# FORMULAIRES DE PARAMÈTRES ET SUPER ADMIN
# ============================================================
class SchoolSettingsForm(FlaskForm):
    name = StringField('Nom de l\'établissement', validators=[DataRequired()])
    director_name = StringField('Nom du Directeur / Proviseur', validators=[DataRequired()])
    address = StringField('Adresse complète', validators=[DataRequired()])
    phone = StringField('Téléphone', validators=[DataRequired()])
    email = StringField('Email officiel', validators=[DataRequired(), Email()])
    logo = FileField('Logo de l\'école (PNG, JPG)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement (jpg, png)!')
    ])
    submit = SubmitField('💾 Enregistrer les paramètres')

class SuperAdminSchoolForm(FlaskForm):
    name = StringField('Nom de l\'établissement', validators=[DataRequired()])
    director_name = StringField('Nom du Directeur', validators=[DataRequired()])
    address = StringField('Adresse', validators=[DataRequired()])
    phone = StringField('Téléphone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    start_date = DateField('Date de début de validité', validators=[DataRequired()])
    end_date = DateField('Date de fin de validité', validators=[DataRequired()])
    status = SelectField('Statut', choices=[
        ('active', '✅ Actif'),
        ('suspended', '⏸️ Suspendu'),
        ('expired', '❌ Expiré')
    ], validators=[DataRequired()])
    submit = SubmitField('💾 Enregistrer l\'établissement')

class UserForm(FlaskForm):
    username = StringField('Identifiant de connexion', validators=[DataRequired(), Length(max=50)])
    password = StringField('Mot de passe', validators=[Optional(), Length(min=6, message="Min. 6 caractères")])
    full_name = StringField('Nom complet', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Téléphone', validators=[Length(max=20)])
    role = SelectField('Rôle', choices=[
        ('super_admin', 'Super Administrateur'),
        ('admin', 'Administrateur / Directeur'),
        ('teacher', 'Enseignant'),
        ('accountant', 'Comptable'),
        ('parent', 'Parent')
    ], validators=[DataRequired()])
    school_id = SelectField('Établissement', coerce=int, validators=[DataRequired()])
    submit = SubmitField('💾 Enregistrer l\'utilisateur')

# ============================================================
# FORMULAIRES WHATSAPP
# ============================================================
class WhatsAppNotificationForm(FlaskForm):
    message_type = SelectField('Type de notification', choices=[
        ('bulletin', '📄 Bulletin de notes (Récapitulatif)'),
        ('absence', '⚠️ Alerte Absence/Retard'),
        ('payment', '💰 Rappel de paiement'),
        ('custom', '📝 Message personnalisé')
    ], validators=[DataRequired()])
    student_id = SelectField('Élève', coerce=int, validators=[DataRequired()])
    custom_message = TextAreaField('Message personnalisé', validators=[Optional()])
    submit = SubmitField('📱 Envoyer par WhatsApp')


class BulkBulletinForm(FlaskForm):
    class_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    term = SelectField('Période', choices=[
        ('Trimestre 1', 'Trimestre 1'),
        ('Trimestre 2', 'Trimestre 2'),
        ('Trimestre 3', 'Trimestre 3'),
        ('Semestre 1', 'Semestre 1'),
        ('Semestre 2', 'Semestre 2'),
        ('Annuel', 'Annuel')
    ], validators=[DataRequired()])
    submit = SubmitField('📱 Lancer l\'envoi groupé des bulletins')