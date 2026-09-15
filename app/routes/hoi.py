from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import db, Student, SchoolSetting

hoi_bp = Blueprint('hoi', __name__, url_prefix='/hoi')

@hoi_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    if current_user.role not in ['hoi', 'school_admin']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    school_id = current_user.school_id
    
    setting = SchoolSetting.query.filter_by(school_id=school_id).first()
    selected_term = request.args.get('term', setting.current_term if setting else 'Term 1')
    selected_year = request.args.get('year', '2026')

    term_field = student_term_status_field(selected_term)

    query = Student.query.filter_by(school_id=school_id)
    if hasattr(Student, 'year'):
        query = query.filter_by(year=selected_year)
    elif hasattr(Student, 'academic_year'):
        query = query.filter_by(academic_year=selected_year)
        
    students = query.all()
    
    total_students = len(students)
    total_exempted = sum(1 for s in students if getattr(s, term_field, '').lower() == 'exempted')
    expected_reams = total_students - total_exempted
    total_received = sum(1 for s in students if getattr(s, term_field, '').lower() == 'submitted')
    
    collection_rate = round((total_received / expected_reams * 100) if expected_reams > 0 else 0, 1)

    return render_template('hoi/dashboard.html',
                           total_students=total_students,
                           expected_reams=expected_reams,
                           total_exempted=total_exempted,
                           total_received=total_received,
                           collection_rate=collection_rate,
                           selected_term=selected_term,
                           selected_year=selected_year)

@hoi_bp.route('/analysis', methods=['GET'])
@login_required
def analysis():
    if current_user.role not in ['hoi', 'school_admin']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    school_id = current_user.school_id
    setting = SchoolSetting.query.filter_by(school_id=school_id).first()
    selected_term = request.args.get('term', setting.current_term if setting else 'Term 1')
    selected_year = request.args.get('year', '2026')
    term_field = student_term_status_field(selected_term)

    query = Student.query.filter_by(school_id=school_id)
    if hasattr(Student, 'year'):
        query = query.filter_by(year=selected_year)
    elif hasattr(Student, 'academic_year'):
        query = query.filter_by(academic_year=selected_year)
        
    students = query.all()

    form_data = {}
    stream_data = {}

    for s in students:
        grade = s.form_grade or 'Unassigned'
        stream = f"{grade} - {s.stream}" if s.stream else f"{grade} - General"
        status = getattr(s, term_field, '').lower()

        if grade not in form_data:
            form_data[grade] = {'total': 0, 'received': 0, 'exempted': 0}
        form_data[grade]['total'] += 1
        if status == 'submitted':
            form_data[grade]['received'] += 1
        elif status == 'exempted':
            form_data[grade]['exempted'] += 1

        if stream not in stream_data:
            stream_data[stream] = {'grade': grade, 'total': 0, 'received': 0, 'exempted': 0}
        stream_data[stream]['total'] += 1
        if status == 'submitted':
            stream_data[stream]['received'] += 1
        elif status == 'exempted':
            stream_data[stream]['exempted'] += 1

    return render_template('hoi/analysis.html',
                           form_data=form_data,
                           stream_data=stream_data,
                           selected_term=selected_term,
                           selected_year=selected_year)

@hoi_bp.route('/compliance-report', methods=['GET'])
@login_required
def compliance_report():
    if current_user.role not in ['hoi', 'school_admin']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))

    school_id = current_user.school_id
    setting = SchoolSetting.query.filter_by(school_id=school_id).first()
    
    selected_term = request.args.get('term', setting.current_term if setting else 'Term 1')
    selected_year = request.args.get('year', '2026')
    selected_grade = request.args.get('form_grade', '')
    selected_stream = request.args.get('stream', '')
    selected_status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    term_field = student_term_status_field(selected_term)

    query = Student.query.filter_by(school_id=school_id)
    if hasattr(Student, 'year'):
        query = query.filter_by(year=selected_year)
    elif hasattr(Student, 'academic_year'):
        query = query.filter_by(academic_year=selected_year)

    if selected_grade:
        query = query.filter_by(form_grade=selected_grade)
    if selected_stream:
        query = query.filter_by(stream=selected_stream)

    all_filtered = query.all()
    
    filtered_students = []
    for s in all_filtered:
        status_val = getattr(s, term_field, 'Pending')
        if not status_val:
            status_val = 'Pending'
        if selected_status and status_val.lower() != selected_status.lower():
            continue
        filtered_students.append({
            'student': s,
            'status': status_val
        })

    per_page = 10
    total_items = len(filtered_students)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = filtered_students[start:end]

    # Get distinct grades
    grades_query = db.session.query(Student.form_grade).filter_by(school_id=school_id)
    if hasattr(Student, 'year'):
        grades_query = grades_query.filter_by(year=selected_year)
    elif hasattr(Student, 'academic_year'):
        grades_query = grades_query.filter_by(academic_year=selected_year)
    grades = [g[0] for g in grades_query.distinct().all() if g[0]]

    # Get distinct streams (optionally filtered by selected grade if chosen)
    streams_query = db.session.query(Student.stream).filter_by(school_id=school_id)
    if hasattr(Student, 'year'):
        streams_query = streams_query.filter_by(year=selected_year)
    elif hasattr(Student, 'academic_year'):
        streams_query = streams_query.filter_by(academic_year=selected_year)
    if selected_grade:
        streams_query = streams_query.filter_by(form_grade=selected_grade)
    streams = [st[0] for st in streams_query.distinct().all() if st[0]]

    return render_template('hoi/compliance_report.html',
                           items=paginated_items,
                           page=page,
                           total_pages=total_pages,
                           total_items=total_items,
                           grades=grades,
                           streams=streams,
                           selected_term=selected_term,
                           selected_year=selected_year,
                           selected_grade=selected_grade,
                           selected_stream=selected_stream,
                           selected_status=selected_status,
                           start_index=start)

def student_term_status_field(term_str):
    if '2' in str(term_str):
        return 'term_2_status'
    elif '3' in str(term_str):
        return 'term_3_status'
    return 'term_1_status'