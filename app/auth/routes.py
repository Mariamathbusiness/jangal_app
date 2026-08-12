from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.auth.forms import LoginForm
from app import login_manager

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si déjà connecté, rediriger selon le rôle
    if current_user.is_authenticated:
        if current_user.role == 'parent':
            return redirect(url_for('parent.dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('pedagogical.dashboard'))
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_username(form.username.data)
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            session['lang'] = 'fr'
            
            # REDIRECTION SELON LE RÔLE APRÈS CONNEXION RÉUSSIE
            if user.role == 'parent':
                return redirect(url_for('parent.dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('pedagogical.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Identifiants invalides', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_language/<lang>')
def change_language(lang):
    if lang in ['fr', 'en', 'ar']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('auth.login'))