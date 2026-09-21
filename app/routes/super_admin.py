from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from ..models import db, School, User, Student
from app.models import db, School, User, ExamRequisition, Student, SchoolSetting

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')

def super_admin_required(f):
    """Decorator to restrict routes strictly to the Super Admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@super_admin_bp.route('/dashboard')
@login_required
@super_admin_required
def dashboard():
    schools = School.query.all()
    total_schools = len(schools)
    active_schools = sum(1 for s in schools if s.is_active)
    suspended_schools = total_schools - active_schools
    total_students = Student.query.count()
    
    return render_template('super_admin/dashboard.html', 
                           schools=schools, 
                           total_schools=total_schools,
                           active_schools=active_schools,
                           suspended_schools=suspended_schools,
                           total_students=total_students)

@super_admin_bp.route('/school/add', methods=['GET', 'POST'])
@login_required
@super_admin_required
def add_school():
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        school_code = request.form.get('school_code')
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')
        
        # Check if school code or username already exists
        if School.query.filter_by(code=school_code).first():
            flash('School code already exists.', 'danger')
            return redirect(url_for('super_admin.add_school'))
            
        if User.query.filter_by(username=admin_username).first():
            flash('Admin username already taken.', 'danger')
            return redirect(url_for('super_admin.add_school'))
            
        # Create School
        new_school = School(name=school_name, code=school_code, is_active=True)
        db.session.add(new_school)
        db.session.commit()
        
        # Create School Admin User
        hashed_password = generate_password_hash(admin_password)
        admin_user = User(
            username=admin_username,
            password_hash=hashed_password,
            role='school_admin',
            school_id=new_school.id
        )
        db.session.add(admin_user)
        db.session.commit()
        
        flash(f'School "{school_name}" and administrator account created successfully.', 'success')
        return redirect(url_for('super_admin.dashboard'))
        
    return render_template('super_admin/add_school.html')

@super_admin_bp.route('/school/toggle/<int:school_id>')
@login_required
@super_admin_required
def toggle_school(school_id):
    school = School.query.get_or_404(school_id)
    school.is_active = not school.is_active
    db.session.commit()
    
    status_msg = "activated" if school.is_active else "suspended"
    flash(f'School "{school.name}" has been {status_msg}.', 'info')
    return redirect(url_for('super_admin.dashboard'))

@super_admin_bp.route('/school/reset-password/<int:school_id>', methods=['POST'])
@login_required
@super_admin_required
def reset_admin_password(school_id):
    school = School.query.get_or_404(school_id)
    new_password = request.form.get('new_password')
    
    admin_user = User.query.filter_by(school_id=school.id, role='school_admin').first()
    if admin_user and new_password:
        admin_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash(f'Password reset successfully for {school.name} administrator.', 'success')
    else:
        flash('Could not reset password. Admin user not found.', 'danger')
        
    return redirect(url_for('super_admin.dashboard'))

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from ..models import db, School, User, Student

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')

def super_admin_required(f):
    """Decorator to restrict routes strictly to the Super Admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@super_admin_bp.route('/dashboard')
@login_required
@super_admin_required
def dashboard():
    schools = School.query.all()
    total_schools = len(schools)
    active_schools = sum(1 for s in schools if s.is_active)
    suspended_schools = total_schools - active_schools
    total_students = Student.query.count()
    
    return render_template('super_admin/dashboard.html', 
                           schools=schools, 
                           total_schools=total_schools,
                           active_schools=active_schools,
                           suspended_schools=suspended_schools,
                           total_students=total_students)

@super_admin_bp.route('/school/add', methods=['GET', 'POST'])
@login_required
@super_admin_required
def add_school():
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        school_code = request.form.get('school_code')
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')
        
        # Check if school code or username already exists
        if School.query.filter_by(code=school_code).first():
            flash('School code already exists.', 'danger')
            return redirect(url_for('super_admin.add_school'))
            
        if User.query.filter_by(username=admin_username).first():
            flash('Admin username already taken.', 'danger')
            return redirect(url_for('super_admin.add_school'))
            
        # Create School
        new_school = School(name=school_name, code=school_code, is_active=True)
        db.session.add(new_school)
        db.session.commit()
        
        # Create School Admin User
        hashed_password = generate_password_hash(admin_password)
        admin_user = User(
            username=admin_username,
            password_hash=hashed_password,
            role='school_admin',
            school_id=new_school.id
        )
        db.session.add(admin_user)
        db.session.commit()
        
        flash(f'School "{school_name}" and administrator account created successfully.', 'success')
        return redirect(url_for('super_admin.dashboard'))
        
    return render_template('super_admin/add_school.html')

@super_admin_bp.route('/school/toggle/<int:school_id>')
@login_required
@super_admin_required
def toggle_school(school_id):
    school = School.query.get_or_404(school_id)
    school.is_active = not school.is_active
    db.session.commit()
    
    status_msg = "activated" if school.is_active else "suspended"
    flash(f'School "{school.name}" has been {status_msg}.', 'info')
    return redirect(url_for('super_admin.dashboard'))

@super_admin_bp.route('/school/reset-password/<int:school_id>', methods=['POST'])
@login_required
@super_admin_required
def reset_admin_password(school_id):
    school = School.query.get_or_404(school_id)
    new_password = request.form.get('new_password')
    
    admin_user = User.query.filter_by(school_id=school.id, role='school_admin').first()
    if admin_user and new_password:
        admin_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash(f'Password reset successfully for {school.name} administrator.', 'success')
    else:
        flash('Could not reset password. Admin user not found.', 'danger')
        
    return redirect(url_for('super_admin.dashboard'))

@super_admin_bp.route('/school/edit/<int:school_id>', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_school(school_id):
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        school_code = request.form.get('school_code')
        
        existing_school = School.query.filter_by(code=school_code).first()
        if existing_school and existing_school.id != school.id:
            flash('School code already taken by another institution.', 'danger')
            return redirect(url_for('super_admin.edit_school', school_id=school.id))
            
        school.name = school_name
        school.code = school_code
        db.session.commit()
        
        flash(f'Institution "{school.name}" updated successfully.', 'success')
        return redirect(url_for('super_admin.dashboard'))
        
    return render_template('super_admin/edit_school.html', school=school)

@super_admin_bp.route('/school/delete/<int:school_id>', methods=['POST'])
@login_required
@super_admin_required
def delete_school(school_id):
    school = School.query.get_or_404(school_id)
    school_name = school.name
    
    # 1. Delete all related child records using school.id first to prevent IntegrityError
    ExamRequisition.query.filter_by(school_id=school.id).delete()
    Student.query.filter_by(school_id=school.id).delete()
    SchoolSetting.query.filter_by(school_id=school.id).delete()
    User.query.filter_by(school_id=school.id).delete()

    # 2. Now safely delete the school itself
    db.session.delete(school)
    db.session.commit()
    
    flash(f'Institution "{school_name}" and all associated records have been deleted.', 'success')
    return redirect(url_for('super_admin.dashboard'))