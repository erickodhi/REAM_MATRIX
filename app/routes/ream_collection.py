from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from ..models import db, Student, SchoolSetting

ream_collection_bp = Blueprint('ream_collection', __name__, url_prefix='/ream-collection')

@ream_collection_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'ream_collection':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    
    # Fetch the settings configured by the School Admin
    setting = SchoolSetting.query.filter_by(school_id=current_user.school_id).first()
    
    # Extract current term string and map it to an integer (1, 2, or 3)
    term_str = setting.current_term if setting and setting.current_term else 'Term 1'
    if '2' in term_str:
        active_term = 2
    elif '3' in term_str:
        active_term = 3
    else:
        active_term = 1

    active_year = setting.current_academic_year if setting and setting.current_academic_year else '2026'

    # Filter students by the active school year set by the admin
    query = Student.query.filter_by(school_id=current_user.school_id, academic_year=active_year)

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Student.full_name.ilike(search_term)) | 
            (Student.admission_no.ilike(search_term))
        )

    pagination = query.order_by(Student.admission_no.asc()).paginate(page=page, per_page=15, error_out=False)
    students = pagination.items

    return render_template(
        'ream_desk/dashboard.html', 
        students=students, 
        pagination=pagination, 
        search_query=search_query,
        active_term=active_term,
        active_year=active_year,
        current_term_label=term_str
    )

@ream_collection_bp.route('/update-status/<int:student_id>', methods=['POST'])
@login_required
def update_status(student_id):
    if current_user.role != 'ream_collection':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    action = request.form.get('action') # 'submit' or 'undo'

    # Read the exact term set by the School Admin
    setting = SchoolSetting.query.filter_by(school_id=current_user.school_id).first()
    term_str = setting.current_term if setting and setting.current_term else 'Term 1'
    
    if '2' in term_str:
        active_term = 2
    elif '3' in term_str:
        active_term = 3
    else:
        active_term = 1

    student = Student.query.get_or_404(student_id)

    if student.school_id != current_user.school_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('ream_collection.dashboard'))

    # Fetch current status for the active term
    current_status = student.term_1_status if active_term == 1 else (student.term_2_status if active_term == 2 else student.term_3_status)

    # BACKEND SAFEGUARD: Block any status change if the student is exempted
    if current_status and current_status.lower() == 'exempted':
        flash(f'Action blocked: {student.full_name} is exempted for {term_str}.', 'warning')
        return redirect(url_for('ream_collection.dashboard', page=request.args.get('page', 1), search=request.args.get('search', '')))

    # Update term status and handle account_owed arithmetic safely
    if action == 'submit' and (not current_status or current_status.lower() != 'submitted'):
        if active_term == 1:
            student.term_1_status = 'Submitted'
        elif active_term == 2:
            student.term_2_status = 'Submitted'
        elif active_term == 3:
            student.term_3_status = 'Submitted'

        # Automatically decrease account owed when a ream is submitted
        if student.account_owed and student.account_owed > 0:
            student.account_owed -= 1

    elif action == 'undo' and current_status and current_status.lower() == 'submitted':
        if active_term == 1:
            student.term_1_status = 'Pending'
        elif active_term == 2:
            student.term_2_status = 'Pending'
        elif active_term == 3:
            student.term_3_status = 'Pending'

        # Restore account owed if a submission is undone by mistake
        student.account_owed = (student.account_owed or 0) + 1

    db.session.commit()
    
    status_msg = 'recorded successfully' if action == 'submit' else 'reverted to pending'
    flash(f'{term_str} status for {student.full_name} {status_msg}.', 'success' if action == 'submit' else 'info')
    
    return redirect(url_for('ream_collection.dashboard', page=request.args.get('page', 1), search=request.args.get('search', '')))