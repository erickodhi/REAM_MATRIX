import csv
import io
import re
from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response
from flask_login import login_required, current_user
from ..models import db, Student, School, User, FormGrade, Stream, SchoolSetting

school_admin_bp = Blueprint('school_admin', __name__, url_prefix='/admin')

def role_required(allowed_roles):
    """Access control decorator to restrict routes to specific user roles within an institution."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.school_id is None:
                flash('Unauthorized access. Please log in.', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                flash('You do not have permission to perform this action.', 'danger')
                return redirect(url_for('school_admin.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@school_admin_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Renders the school admin dashboard with year-based filtering and student records."""
    if current_user.role == 'super_admin':
        return redirect(url_for('super_admin.dashboard'))
        
    search_query = request.args.get('search', '').strip()
    selected_year = request.args.get('year', '').strip()
    school_id = current_user.school_id
    
    settings = SchoolSetting.query.filter_by(school_id=school_id).first()
    if not settings:
        settings = SchoolSetting(school_id=school_id, current_term='Term 1', current_academic_year='2026')
        db.session.add(settings)
        db.session.commit()
        
    if not selected_year:
        selected_year = settings.current_academic_year
        
    query = Student.query.filter_by(school_id=school_id, academic_year=selected_year)
    if search_query:
        query = query.filter(Student.admission_no.ilike(f'%{search_query}%'))
        
    students = query.order_by(Student.admission_no.asc()).all()
    school = School.query.get(school_id)
    
    available_years = db.session.query(Student.academic_year).filter_by(school_id=school_id).distinct().all()
    available_years = [y[0] for y in available_years]
    if selected_year not in available_years:
        available_years.append(selected_year)
    available_years.sort(reverse=True)
        
    forms = FormGrade.query.filter_by(school_id=school_id).all()
    streams = Stream.query.filter_by(school_id=school_id).all()
    
    return render_template('school_admin/dashboard.html', 
                           students=students, 
                           school=school, 
                           settings=settings,
                           forms=forms,
                           streams=streams,
                           search_query=search_query,
                           available_years=available_years,
                           selected_year=selected_year)


@school_admin_bp.route('/student/promote', methods=['POST'])
@login_required
@role_required(['school_admin'])
def promote_students():
    school_id = current_user.school_id
    new_year = request.form.get('next_academic_year').strip()
    
    if not new_year:
        flash('Please specify a valid target academic year for promotion.', 'danger')
        return redirect(url_for('school_admin.dashboard'))
        
    settings = SchoolSetting.query.filter_by(school_id=school_id).first()
    current_active_year = settings.current_academic_year if settings else '2026'
    
    current_students = Student.query.filter_by(school_id=school_id, academic_year=current_active_year).all()
    
    promoted_count = 0
    skipped_count = 0
    
    for s in current_students:
        form_lower = s.form_grade.lower() if s.form_grade else ''
        if 'form 4' in form_lower or 'form iv' in form_lower or 'grade 12' in form_lower or 'grade xii' in form_lower:
            skipped_count += 1
            continue
            
        existing_in_new_year = Student.query.filter_by(
            school_id=school_id, 
            admission_no=s.admission_no, 
            academic_year=new_year
        ).first()
        
        if not existing_in_new_year:
            new_form_grade = s.form_grade
            if new_form_grade:
                match = re.search(r'\d+', new_form_grade)
                if match:
                    current_num = int(match.group())
                    next_num = current_num + 1
                    new_form_grade = new_form_grade.replace(str(current_num), str(next_num))
            
            new_student = Student(
                school_id=school_id,
                admission_no=s.admission_no,
                full_name=s.full_name,
                gender=s.gender,
                form_grade=new_form_grade,
                stream=s.stream,
                enrollment_term='Term 1',
                academic_year=new_year,
                term_1_status='Pending',
                term_2_status='Pending',
                term_3_status='Pending',
                account_owed=3
            )
            db.session.add(new_student)
            promoted_count += 1
            
    if settings:
        settings.current_academic_year = new_year
        settings.current_term = 'Term 1'
        
    db.session.commit()
    flash(f'Successfully promoted {promoted_count} students to academic year {new_year}. {skipped_count} final-year students were left in their terminal year as historical graduates.', 'success')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/settings/update', methods=['POST'])
@login_required
@role_required(['school_admin'])
def update_settings():
    school_id = current_user.school_id
    term = request.form.get('current_term')
    year = request.form.get('current_academic_year').strip()
    
    settings = SchoolSetting.query.filter_by(school_id=school_id).first()
    if not settings:
        settings = SchoolSetting(school_id=school_id)
        db.session.add(settings)
        
    settings.current_term = term
    settings.current_academic_year = year
    db.session.commit()
    
    flash('Academic term and year settings updated successfully.', 'success')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/config/add-form', methods=['POST'])
@login_required
@role_required(['school_admin'])
def add_form():
    name = request.form.get('form_name').strip()
    if name:
        existing = FormGrade.query.filter_by(school_id=current_user.school_id, name=name).first()
        if not existing:
            db.session.add(FormGrade(school_id=current_user.school_id, name=name))
            db.session.commit()
            flash(f'Form/Grade "{name}" added successfully.', 'success')
        else:
            flash(f'Form/Grade "{name}" already exists.', 'warning')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/config/add-stream', methods=['POST'])
@login_required
@role_required(['school_admin'])
def add_stream():
    name = request.form.get('stream_name').strip()
    if name:
        existing = Stream.query.filter_by(school_id=current_user.school_id, name=name).first()
        if not existing:
            db.session.add(Stream(school_id=current_user.school_id, name=name))
            db.session.commit()
            flash(f'Stream "{name}" added successfully.', 'success')
        else:
            flash(f'Stream "{name}" already exists.', 'warning')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/student/add', methods=['GET', 'POST'])
@login_required
@role_required(['school_admin'])
def add_student():
    school_id = current_user.school_id
    settings = SchoolSetting.query.filter_by(school_id=school_id).first()
    forms = FormGrade.query.filter_by(school_id=school_id).all()
    streams = Stream.query.filter_by(school_id=school_id).all()
    
    if request.method == 'POST':
        admission_no = request.form.get('admission_no').strip()
        full_name = request.form.get('full_name').strip()
        gender = request.form.get('gender')
        form_grade = request.form.get('form_grade')
        stream = request.form.get('stream')
        enrollment_term = request.form.get('enrollment_term')
        academic_year = settings.current_academic_year if settings else '2026'
        
        existing = Student.query.filter_by(school_id=school_id, admission_no=admission_no).first()
        if existing:
            flash(f'Admission Number "{admission_no}" already exists in the system.', 'danger')
            return redirect(url_for('school_admin.add_student'))
            
        if enrollment_term == 'Term 1':
            t1, t2, t3 = 'Pending', 'Pending', 'Pending'
            account_owed = 3.0
        elif enrollment_term == 'Term 2':
            t1, t2, t3 = 'Exempted', 'Pending', 'Pending'
            account_owed = 2.0
        else: 
            t1, t2, t3 = 'Exempted', 'Exempted', 'Pending'
            account_owed = 1.0
            
        new_student = Student(
            school_id=school_id,
            admission_no=admission_no,
            full_name=full_name,
            gender=gender,
            form_grade=form_grade,
            stream=stream,
            enrollment_term=enrollment_term,
            academic_year=academic_year,
            term_1_status=t1,
            term_2_status=t2,
            term_3_status=t3,
            account_owed=account_owed
        )
        db.session.add(new_student)
        db.session.commit()
        
        flash(f'Student {full_name} enrolled successfully with automatic balance of {account_owed} reams.', 'success')
        return redirect(url_for('school_admin.dashboard'))
        
    return render_template('school_admin/add_student.html', forms=forms, streams=streams, settings=settings)


@school_admin_bp.route('/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
@role_required(['school_admin'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if student.school_id != current_user.school_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('school_admin.dashboard'))
        
    school_id = current_user.school_id
    forms = FormGrade.query.filter_by(school_id=school_id).all()
    streams = Stream.query.filter_by(school_id=school_id).all()
    
    if request.method == 'POST':
        student.admission_no = request.form.get('admission_no').strip()
        student.full_name = request.form.get('full_name').strip()
        student.gender = request.form.get('gender')
        student.form_grade = request.form.get('form_grade')
        student.stream = request.form.get('stream')
        student.account_owed = float(request.form.get('account_owed', 0.0))
        
        db.session.commit()
        flash(f'Record for {student.full_name} updated successfully.', 'success')
        return redirect(url_for('school_admin.dashboard'))
        
    return render_template('school_admin/edit_student.html', student=student, forms=forms, streams=streams)


@school_admin_bp.route('/student/bulk-enroll', methods=['POST'])
@login_required
@role_required(['school_admin'])
def bulk_enroll():
    file = request.files.get('bulk_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'danger')
        return redirect(url_for('school_admin.dashboard'))
        
    school_id = current_user.school_id
    settings = SchoolSetting.query.filter_by(school_id=school_id).first()
    academic_year = settings.current_academic_year if settings else '2026'
    
    stream_file = io.TextIOWrapper(file.stream, encoding='utf-8')
    reader = csv.DictReader(stream_file)
    
    count = 0
    for row in reader:
        adm = row.get('admission_no', '').strip()
        name = row.get('full_name', '').strip()
        gender = row.get('gender', '').strip()
        form = row.get('form_grade', '').strip()
        strm = row.get('stream', '').strip()
        term = row.get('enrollment_term', 'Term 1').strip()
        
        if adm and name:
            if not Student.query.filter_by(school_id=school_id, admission_no=adm).first():
                if term == 'Term 1':
                    t1, t2, t3 = 'Pending', 'Pending', 'Pending'
                    account_owed = 3.0
                elif term == 'Term 2':
                    t1, t2, t3 = 'Exempted', 'Pending', 'Pending'
                    account_owed = 2.0
                else:
                    t1, t2, t3 = 'Exempted', 'Exempted', 'Pending'
                    account_owed = 1.0

                student = Student(
                    school_id=school_id, admission_no=adm, full_name=name, gender=gender,
                    form_grade=form, stream=strm, enrollment_term=term, academic_year=academic_year,
                    term_1_status=t1, term_2_status=t2, term_3_status=t3, account_owed=account_owed
                )
                db.session.add(student)
                count += 1
                
    db.session.commit()
    flash(f'Successfully bulk enrolled {count} students with automatic ream balances.', 'success')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/student/download-template', methods=['GET'])
@login_required
@role_required(['school_admin'])
def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['admission_no', 'full_name', 'gender', 'form_grade', 'stream', 'enrollment_term'])
    writer.writerow(['ADM/001', 'Jane Doe', 'Female', 'Form 1', 'East', 'Term 1'])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=bulk_enrollment_template.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@school_admin_bp.route('/student/delete-by-year', methods=['POST'])
@login_required
@role_required(['school_admin'])
def delete_by_year():
    school_id = current_user.school_id
    target_year = request.form.get('target_year').strip()
    
    deleted_count = Student.query.filter_by(school_id=school_id, academic_year=target_year).delete()
    db.session.commit()
    
    flash(f'Successfully deleted {deleted_count} student records associated with academic year {target_year}.', 'warning')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/student/delete/<int:student_id>', methods=['GET'])
@login_required
@role_required(['school_admin'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    if student.school_id != current_user.school_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('school_admin.dashboard'))
        
    db.session.delete(student)
    db.session.commit()
    
    flash('Student record deleted successfully.', 'info')
    return redirect(url_for('school_admin.dashboard'))


@school_admin_bp.route('/staff')
@login_required
def manage_staff():
    if current_user.role != 'school_admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('school_admin.dashboard'))
        
    staff_members = User.query.filter_by(school_id=current_user.school_id).all()
    return render_template('school_admin/manage_staff.html', staff_members=staff_members)


@school_admin_bp.route('/staff/add', methods=['POST'])
@login_required
def add_staff():
    if current_user.role != 'school_admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('school_admin.dashboard'))

    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('A user with that username already exists.', 'danger')
        return redirect(url_for('school_admin.dashboard'))

    new_staff = User(
        username=username,
        role=role,
        school_id=current_user.school_id
    )
    new_staff.set_password(password)
    
    db.session.add(new_staff)
    db.session.commit()

    flash(f'Staff member {username} created successfully!', 'success')
    return redirect(url_for('school_admin.dashboard'))

@school_admin_bp.route('/edit-staff/<int:staff_id>', methods=['GET', 'POST'])
@login_required
def edit_staff(staff_id):
    if current_user.role != 'school_admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch the staff member (ensuring they belong to the same school)
    staff = User.query.get_or_404(staff_id)
    if staff.school_id != current_user.school_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('school_admin.manage_staff'))

    if request.method == 'POST':
        staff.username = request.form.get('username')
        staff.email = request.form.get('email')
        staff.role = request.form.get('role')
        
        # Optional: update password only if a new one is provided
        new_password = request.form.get('password')
        if new_password:
            staff.set_password(new_password) # Replace with your hashing method if using bcrypt/argon2 directly

        db.session.commit()
        flash(f'Staff member {staff.username} updated successfully!', 'success')
        return redirect(url_for('school_admin.manage_staff'))

    return render_template('school_admin/edit_staff.html', staff=staff)