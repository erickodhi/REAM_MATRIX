import math
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, ExamRequisition, StoreCollection, Student
from flask_login import login_required, current_user
# Import your models (ExamRequisition, StoreCollection, db, etc.)
from app.models import db, ExamRequisition, StoreCollection
exam_bp = Blueprint('exam', __name__)

@exam_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    school_id = current_user.school_id
    requisitions = ExamRequisition.query.filter_by(school_id=school_id).order_by(ExamRequisition.date_requested.desc()).all()
    
    # 1. Calculate Total Collected based on student ream submissions (500 sheets per ream)
    submitted_students = Student.query.filter_by(school_id=school_id).filter(
        (Student.term_1_status == 'Submitted') | 
        (Student.term_2_status == 'Submitted') | 
        (Student.term_3_status == 'Submitted')
    ).count()
    
    total_collected = submitted_students * 500
    
    # 2. Calculate Total Issued (Only full reams pull from the main store inventory)
    total_issued = sum(
        r.full_reams_to_issue * 500 
        for r in requisitions 
        if r.status != 'Rejected' and not r.is_loose_disbursement
    )
    
    # 3. Calculate current loose leftover pool minus already disbursed loose sheets
    total_loose_generated = sum(
        r.leftover_loose_sheets for r in requisitions 
        if r.status in ['Pending', 'Approved', 'Issued'] and not r.is_loose_disbursement
    )
    
    total_loose_disbursed = sum(
        r.total_sheets_required for r in requisitions 
        if r.is_loose_disbursement and r.status != 'Rejected'
    )
    
    current_loose_leftovers = total_loose_generated - total_loose_disbursed
    
    available_balance = total_collected - total_issued
    
    # Handle Full Ream Requisition Submission from Verification Modal
    if request.method == 'POST' and request.form.get('action_type') == 'ream_requisition':
        # Safety Check 1: No collection made yet
        if total_collected <= 0:
            flash('Cannot process requisition: No paper reams have been collected into the store yet!', 'danger')
            return redirect(url_for('exam.dashboard'))
            
        num_students = int(request.form.get('num_students', 0))
        sheets_per_student = int(request.form.get('sheets_per_student', 0))
        exam_sheets = num_students * sheets_per_student
        padding_sheets = 100
        total_required = exam_sheets + padding_sheets
        
        full_reams = math.ceil(total_required / 500)
        required_sheets_from_store = full_reams * 500
        
        # Safety Check 2: Request exceeds total store inventory balance
        if required_sheets_from_store > available_balance:
            flash(f'Requisition exceeds store balance! Requested {full_reams} reams ({required_sheets_from_store} sheets), but only {available_balance} sheets remain in store.', 'danger')
            return redirect(url_for('exam.dashboard'))

        leftover_loose = required_sheets_from_store - total_required

        new_req = ExamRequisition(
            school_id=school_id,
            department_subject=request.form.get('department_subject'),
            teacher_name=request.form.get('teacher_name'),
            purpose=request.form.get('purpose'),
            form_grade=request.form.get('form_grade'),
            num_students=num_students,
            sheets_per_student=sheets_per_student,
            padding_sheets=padding_sheets,
            total_sheets_required=total_required,
            full_reams_to_issue=full_reams,
            leftover_loose_sheets=leftover_loose,
            is_loose_disbursement=False,
            status='Approved'
        )
        db.session.add(new_req)
        db.session.commit()
        flash('Exam ream requisition successfully verified and approved!', 'success')
        return redirect(url_for('exam.dashboard'))

    return render_template(
        'exam/dashboard.html',
        requisitions=requisitions,
        total_collected=total_collected,
        total_issued=total_issued,
        current_loose_leftovers=current_loose_leftovers,
        available_balance=available_balance
    )

@exam_bp.route('/disburse-loose', methods=['POST'])
@login_required
def disburse_loose():
    school_id = current_user.school_id
    sheets_requested = int(request.form.get('sheets_requested', 0))
    
    # Recalculate loose leftovers securely
    requisitions = ExamRequisition.query.filter_by(school_id=school_id).all()
    current_loose_leftovers = sum(
        r.leftover_loose_sheets for r in requisitions 
        if r.status in ['Pending', 'Approved', 'Issued'] and not r.is_loose_disbursement
    )
    
    if sheets_requested > current_loose_leftovers:
        flash(f'Disbursement failed: Requested {sheets_requested} sheets exceeds available loose pool ({current_loose_leftovers} sheets).', 'danger')
        return redirect(url_for('exam.dashboard'))

    new_disburse = ExamRequisition(
        school_id=school_id,
        department_subject=request.form.get('department_subject'),
        teacher_name=request.form.get('teacher_name'),
        purpose=request.form.get('purpose'),
        form_grade=request.form.get('form_grade'),
        num_students=0,
        sheets_per_student=0,
        padding_sheets=0,
        total_sheets_required=sheets_requested,
        full_reams_to_issue=0,
        leftover_loose_sheets=0,
        is_loose_disbursement=True,
        status='Completed'
    )
    db.session.add(new_disburse)
    db.session.commit()
    flash(f'Successfully disbursed {sheets_requested} loose sheets from the store pool!', 'success')
    return redirect(url_for('exam.dashboard'))