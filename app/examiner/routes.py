from datetime import datetime, date, time
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import examiner_bp
from ..models import (
    db, User, ExaminerProfile, Examination, ExaminationRubric,
    ExaminationSlot, Booking, Evaluation, EvaluationScore
)

def examiner_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_examiner:
            flash('Access denied. Examiner privileges required.', 'danger')
            return redirect(url_for('index'))
        if not current_user.is_approved_examiner:
            flash('Your examiner account is not approved yet. Please wait for Admin approval.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- EXAMINER DASHBOARD -----------------
@examiner_bp.route('/dashboard')
@examiner_required
def dashboard():
    # Created slots by this examiner
    my_slots = ExaminationSlot.query.filter_by(examiner_id=current_user.id).order_by(
        ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.asc()
    ).all()
    
    # Examinations where slot creation is open
    available_exams = Examination.query.filter(
        Examination.status.in_(['Slot Creation', 'Booking Open'])
    ).all()

    # Total students booked in this examiner's slots
    total_booked_students = Booking.query.join(ExaminationSlot).filter(
        ExaminationSlot.examiner_id == current_user.id,
        Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])
    ).count()

    # Pending evaluations
    my_slot_ids = [s.id for s in my_slots]
    pending_evaluations_count = 0
    if my_slot_ids:
        pending_evaluations_count = Booking.query.filter(
            Booking.slot_id.in_(my_slot_ids),
            Booking.status.in_(['Booked', 'Rescheduled']),
            ~Booking.evaluation.has()
        ).count()

    stats = {
        'total_slots': len(my_slots),
        'total_booked': total_booked_students,
        'pending_evaluations': pending_evaluations_count,
        'active_exams': len(available_exams)
    }

    return render_template(
        'examiner/dashboard.html',
        stats=stats,
        my_slots=my_slots[:5],
        available_exams=available_exams
    )

# ----------------- SLOTS MANAGEMENT -----------------
@examiner_bp.route('/slots')
@examiner_required
def slots():
    my_slots = ExaminationSlot.query.filter_by(examiner_id=current_user.id).order_by(
        ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.asc()
    ).all()
    return render_template('examiner/slots.html', slots=my_slots)

@examiner_bp.route('/slots/create', methods=['GET', 'POST'])
@examiner_required
def create_slot():
    exam_id = request.args.get('exam_id', type=int)
    # Only show examinations where slot creation is allowed
    all_exams = Examination.query.filter(
        Examination.status.in_(['Slot Creation', 'Draft', 'Booking Open'])
    ).all()
    # Filter strictly by slot creation permission
    open_exams = [e for e in all_exams if e.is_slot_creation_open()]

    if request.method == 'POST':
        selected_exam_id = request.form.get('examination_id', type=int)
        exam = Examination.query.get_or_404(selected_exam_id)

        # Enforcement: Examiners can create slots ONLY during the slot creation period
        if not exam.is_slot_creation_open():
            flash('Slot creation is currently closed for this examination.', 'danger')
            return redirect(url_for('examiner.create_slot'))

        slot_date_str = request.form.get('slot_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        max_capacity = request.form.get('max_capacity', type=int) or 1
        location_or_link = request.form.get('location_or_link', '').strip()

        if not all([slot_date_str, start_time_str, end_time_str]):
            flash('Please specify date, start time, and end time.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=open_exams, selected_exam_id=exam_id)

        try:
            s_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
            s_time = datetime.strptime(start_time_str, '%H:%M').time()
            e_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=open_exams, selected_exam_id=exam_id)

        if s_time >= e_time:
            flash('Start time must be before end time.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=open_exams, selected_exam_id=exam_id)

        new_slot = ExaminationSlot(
            examination_id=exam.id,
            examiner_id=current_user.id,
            slot_date=s_date,
            start_time=s_time,
            end_time=e_time,
            max_capacity=max_capacity,
            available_seats=max_capacity,
            status='Available',
            location_or_link=location_or_link or 'Online / Room 101'
        )
        db.session.add(new_slot)
        db.session.commit()
        flash('Examination slot created successfully.', 'success')
        return redirect(url_for('examiner.slots'))

    return render_template('examiner/slot_form.html', action='Create', slot=None, exams=open_exams, selected_exam_id=exam_id)

@examiner_bp.route('/slots/<int:slot_id>/edit', methods=['GET', 'POST'])
@examiner_required
def edit_slot(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    if slot.examiner_id != current_user.id:
        flash('You cannot edit slots created by other examiners.', 'danger')
        return redirect(url_for('examiner.slots'))

    # Enforcement: Examiners can update or remove slots BEFORE booking starts (no active bookings)
    if not slot.is_modifiable:
        flash('Cannot update this slot because students have already booked it.', 'danger')
        return redirect(url_for('examiner.slots'))

    all_exams = [slot.examination]

    if request.method == 'POST':
        slot_date_str = request.form.get('slot_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        max_capacity = request.form.get('max_capacity', type=int) or 1
        location_or_link = request.form.get('location_or_link', '').strip()

        try:
            s_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
            s_time = datetime.strptime(start_time_str, '%H:%M').time()
            e_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return render_template('examiner/slot_form.html', action='Edit', slot=slot, exams=all_exams, selected_exam_id=slot.examination_id)

        if s_time >= e_time:
            flash('Start time must be before end time.', 'danger')
            return render_template('examiner/slot_form.html', action='Edit', slot=slot, exams=all_exams, selected_exam_id=slot.examination_id)

        slot.slot_date = s_date
        slot.start_time = s_time
        slot.end_time = e_time
        slot.max_capacity = max_capacity
        slot.available_seats = max_capacity
        slot.location_or_link = location_or_link
        db.session.commit()

        flash('Slot updated successfully.', 'success')
        return redirect(url_for('examiner.slots'))

    return render_template('examiner/slot_form.html', action='Edit', slot=slot, exams=all_exams, selected_exam_id=slot.examination_id)

@examiner_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
@examiner_required
def delete_slot(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    if slot.examiner_id != current_user.id:
        flash('You cannot delete slots created by other examiners.', 'danger')
        return redirect(url_for('examiner.slots'))

    # Enforcement: Cannot remove slot once student bookings exist
    if not slot.is_modifiable:
        flash('Cannot delete this slot because students have already booked it.', 'danger')
        return redirect(url_for('examiner.slots'))

    db.session.delete(slot)
    db.session.commit()
    flash('Examination slot removed successfully.', 'info')
    return redirect(url_for('examiner.slots'))

# ----------------- VIEW STUDENTS & EVALUATE -----------------
@examiner_bp.route('/slots/<int:slot_id>/students')
@examiner_required
def slot_students(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    if slot.examiner_id != current_user.id:
        flash('You can only view students booked in your own slots.', 'danger')
        return redirect(url_for('examiner.slots'))

    bookings = slot.bookings.all()
    return render_template('examiner/slot_students.html', slot=slot, bookings=bookings)

@examiner_bp.route('/bookings/<int:booking_id>/evaluate', methods=['GET', 'POST'])
@examiner_required
def evaluate_student(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = booking.slot

    # Enforcement: Examiners can evaluate ONLY students booked into their own slots
    if slot.examiner_id != current_user.id:
        flash('Security policy: You can only evaluate students booked in your own slots.', 'danger')
        return redirect(url_for('examiner.dashboard'))

    exam = slot.examination
    rubrics = exam.rubrics.all()
    existing_evaluation = booking.evaluation

    if request.method == 'POST':
        remarks = request.form.get('remarks', '').strip()
        total_marks = 0.0

        if existing_evaluation:
            eval_obj = existing_evaluation
            eval_obj.remarks = remarks
            eval_obj.evaluated_at = datetime.utcnow()
            # Clear previous scores to overwrite
            EvaluationScore.query.filter_by(evaluation_id=eval_obj.id).delete()
        else:
            eval_obj = Evaluation(
                booking_id=booking.id,
                examiner_id=current_user.id,
                total_marks_awarded=0.0,
                remarks=remarks,
                status='Submitted'
            )
            db.session.add(eval_obj)
            db.session.flush()

        # Parse score for each rubric criterion
        for rubric in rubrics:
            field_name = f'rubric_marks_{rubric.id}'
            remarks_name = f'rubric_remarks_{rubric.id}'
            score_val = request.form.get(field_name, type=float) or 0.0
            crit_remark = request.form.get(remarks_name, '').strip()

            # Ensure score does not exceed rubric max marks
            score_val = min(max(0.0, score_val), rubric.max_marks)
            total_marks += score_val

            score_record = EvaluationScore(
                evaluation_id=eval_obj.id,
                rubric_id=rubric.id,
                marks_awarded=score_val,
                remarks=crit_remark
            )
            db.session.add(score_record)

        eval_obj.total_marks_awarded = total_marks
        booking.status = 'Completed'
        db.session.commit()

        flash(f'Evaluation submitted successfully for {booking.student.full_name}. Awarded Marks: {total_marks}/{exam.max_marks}', 'success')
        return redirect(url_for('examiner.slot_students', slot_id=slot.id))

    # Preload existing scores if editing evaluation
    scores_dict = {}
    if existing_evaluation:
        for s in existing_evaluation.scores:
            scores_dict[s.rubric_id] = s

    return render_template(
        'examiner/evaluate_student.html',
        booking=booking,
        exam=exam,
        rubrics=rubrics,
        evaluation=existing_evaluation,
        scores_dict=scores_dict
    )
