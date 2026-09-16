import math
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, ExamRequisition, StoreCollection, Student, SchoolSetting

exam_bp = Blueprint('exam', __name__)

@exam_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    school_id = current_user.school_id
    requisitions = ExamRequisition.query.filter_by(school_id=school_id).order_by(ExamRequisition.date_requested.desc()).all()
    
    # 1. Calculate Total Collected summing collections independently per term (case-insensitive)
    t1_submitted = Student.query.filter_by(school_id=school_id).filter(db.func.lower(Student.term_1_status) == 'submitted').count()
    t2_submitted = Student.query.filter_by(school_id=school_id).filter(db.func.lower(Student.term_2_status) == 'submitted').count()
    t3_submitted = Student.query.filter_by(school_id=school_id).filter(db.func.lower(Student.term_3_status) == 'submitted').count()
    
    total_collected_reams = t1_submitted + t2_submitted + t3_submitted
    total_collected = total_collected_reams * 500
    
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

        # --- TRIGGER HOI SMS NOTIFICATION ---
        send_hoi_sms_notification(school_id, new_req, total_issued, available_balance)
        # ------------------------------------

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


def send_hoi_sms_notification(school_id, req, total_issued_sheets, available_balance_sheets):
    # Fetch the school setting configured by the HOI themselves
    setting = SchoolSetting.query.filter_by(school_id=school_id).first()
    
    if not setting or not setting.sms_phone:
        return  # No phone number configured by the HOI yet

    total_issued_reams = total_issued_sheets / 500
    available_balance_reams = available_balance_sheets / 500

    message = (
        f"REAM ALERT: Reams issued for {req.department_subject} "
        f"by {req.teacher_name} ({req.purpose}). "
        f"Issued: {req.full_reams_to_issue} Reams. "
        f"Total Exam Office Issued: {total_issued_reams:.1f} Reams. "
        f"Store Balance: {available_balance_reams:.1f} Reams."
    )

    # --- Replace with your actual SMS provider details ---
    api_url = "https://api.your-sms-provider.com/send"  # e.g., Africa's Talking or Twilio URL
    api_key = "YOUR_SMS_API_KEY"                      # Your gateway secret key
    
    payload = {
        "to": setting.sms_phone,                      # Uses the number the HOI entered in Settings!
        "message": message,
        "from": "REAM_MATRIX"
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        requests.post(api_url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"SMS Gateway Error: {e}")