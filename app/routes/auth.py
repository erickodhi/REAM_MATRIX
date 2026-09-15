from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from ..models import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'super_admin':
            return redirect(url_for('super_admin.dashboard'))
        elif current_user.role == 'school_admin':
            return redirect(url_for('school_admin.dashboard'))
        elif current_user.role == 'exam_officer':
            return redirect(url_for('exam.dashboard'))
        elif current_user.role == 'ream_collection':
            return redirect(url_for('ream_collection.dashboard'))
        elif current_user.role == 'hoi':
            return redirect(url_for('hoi.dashboard'))
        else:
            logout_user()
            flash('Your dedicated dashboard is currently under construction.', 'info')
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role == 'super_admin':
                return redirect(url_for('super_admin.dashboard'))
            elif user.role == 'school_admin':
                return redirect(url_for('school_admin.dashboard'))
            elif user.role == 'exam_officer':
                return redirect(url_for('exam.dashboard'))
            elif user.role == 'ream_collection':
                return redirect(url_for('ream_collection.dashboard'))
            elif user.role == 'hoi':
                return redirect(url_for('hoi.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/suspended')
def suspended():
    return render_template('auth/suspended.html')