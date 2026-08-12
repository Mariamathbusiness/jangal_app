from flask import Blueprint, render_template
from flask_login import login_required

parent_bp = Blueprint('parent', __name__, template_folder='../templates/parent')

@parent_bp.route('/')
@login_required
def index():
    return "👨‍👩‍👧 Portail Parent (En cours de développement)"

@parent_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('parent/dashboard.html') # Nous créerons ce fichier plus tard