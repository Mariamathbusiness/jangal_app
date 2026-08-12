from flask import Blueprint, render_template
from flask_login import login_required

pedagogical_bp = Blueprint('pedagogical', __name__, template_folder='../templates/pedagogical')

@pedagogical_bp.route('/')
@login_required
def index():
    return "📚 Module Pédagogique (En cours de développement)"

@pedagogical_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('pedagogical/dashboard.html') # Nous créerons ce fichier plus tard