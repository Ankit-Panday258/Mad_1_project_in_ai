from datetime import datetime, date
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import student_bp
from ..models import (
    db, User, StudentProfile, Course, Examination, ExaminationRubric,
    ExaminationSlot, Booking, Evaluation
)

def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_student:
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- STUDENT DASHBOARD -----------------
@student_bp.route('/dashboard')
@student_required
def dashboard():
    today = date.today()

    # Active student bookings
    all_bookings = Booking.query.filter_by(student_id=current_user.id).order_by(
        Booking.created_at.desc()
    ).all()

    active_bookings = [b for b in all_bookings if b.status in ['Booked', 'Rescheduled']]
    completed_evaluations = [b for b in all_bookings if b.evaluation is not None]

    # Available examinations currently open for booking
    all_exams = Examination.query.all()
    open_exams = [e for e in all_exams if e.is_slot_booking_open()]

    # Available slots across open exams
    open_exam_ids = [e.id for e in open_exams]
    available_slots_count = ExaminationSlot.query.filter(
        ExaminationSlot.examination_id.in_(open_exam_ids),
        ExaminationSlot.available_seats > 0,
        ExaminationSlot.status == 'Available'
    ).count() if open_exam_ids else 0

    stats = {
        'open_exams_count': len(open_exams),
        'available_slots_count': available_slots_count,
        'my_active_bookings': len(active_bookings),
        'results_published': len(completed_evaluations)
    }

    return render_template(
        'student/dashboard.html',
        stats=stats,
        active_bookings=active_bookings,
        open_exams=open_exams[:4],
        completed_evaluations=completed_evaluations[:4]
    )

# ----------------- EXAMINATIONS & CATALOG -----------------
@student_bp.route('/examinations')
@student_required
def examinations():
    search_q = request.args.get('q', '').strip()
    course_filter = request.args.get('course_id', type=int)
    type_filter = request.args.get('type', '').strip()

    query = Examination.query.join(Course)
    if search_q:
        query = query.filter(
            (Examination.examination_name.ilike(f'%{search_q}%')) |
            (Course.course_name.ilike(f'%{search_q}%')) |
            (Course.course_code.ilike(f'%{search_q}%'))
        )
    if course_filter:
        query = query.filter(Examination.course_id == course_filter)
    if type_filter:
        query = query.filter(Examination.examination_type == type_filter)

    exams_list = query.order_by(Examination.slot_booking_start_date.desc()).all()
    courses_list = Course.query.filter_by(status='active').all()

    # Track which exams student already has active bookings for
    my_active_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).all()
    booked_exam_ids = {b.slot.examination_id for b in my_active_bookings}

    return render_template(
        'student/examinations.html',
        examinations=exams_list,
        courses=courses_list,
        booked_exam_ids=booked_exam_ids,
        search_q=search_q,
        course_filter=course_filter,
        type_filter=type_filter
    )

@student_bp.route('/examinations/<int:exam_id>/slots')
@student_required
def exam_slots(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    slots_list = ExaminationSlot.query.filter_by(examination_id=exam.id).order_by(
        ExaminationSlot.slot_date.asc(), ExaminationSlot.start_time.asc()
    ).all()

    # Check if student already booked a slot for this exam
    existing_booking = Booking.query.join(ExaminationSlot).filter(
        Booking.student_id == current_user.id,
        ExaminationSlot.examination_id == exam.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).first()

    return render_template(
        'student/exam_slots.html',
        exam=exam,
        slots=slots_list,
        existing_booking=existing_booking
    )

# ----------------- BOOKING & CANCELLATION -----------------
@student_bp.route('/slots/<int:slot_id>/book', methods=['POST'])
@student_required
def book_slot(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    exam = slot.examination

    # Rule 1: Students can book slots ONLY during the booking period
    if not exam.is_slot_booking_open():
        flash('Booking is not currently open for this examination.', 'danger')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # Rule 2: Prevent duplicate bookings for the same examination
    existing_booking = Booking.query.join(ExaminationSlot).filter(
        Booking.student_id == current_user.id,
        ExaminationSlot.examination_id == exam.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).first()

    if existing_booking:
        flash(f'You have already booked a slot for "{exam.examination_name}". Duplicate booking is prohibited.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # Rule 3: Prevent overbooking beyond slot capacity
    if slot.available_seats <= 0 or slot.status != 'Available':
        flash('Sorry, this slot is fully booked or no longer available.', 'danger')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # Create booking
    new_booking = Booking(
        student_id=current_user.id,
        slot_id=slot.id,
        status='Booked'
    )
    db.session.add(new_booking)
    db.session.flush()

    # Update slot seats & auto-close if reached
    slot.sync_availability()
    db.session.commit()

    flash(f'Successfully booked slot for "{exam.examination_name}" on {slot.slot_date} ({slot.start_time.strftime("%H:%M")})!', 'success')
    return redirect(url_for('student.bookings'))

@student_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@student_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.student_id != current_user.id:
        flash('Unauthorized cancellation request.', 'danger')
        return redirect(url_for('student.bookings'))

    if booking.status not in ['Booked', 'Rescheduled']:
        flash('This booking cannot be cancelled because it is already completed or cancelled.', 'warning')
        return redirect(url_for('student.bookings'))

    slot = booking.slot
    exam = slot.examination
    today = date.today()

    # Rule: Can cancel booking BEFORE the booking deadline
    if today > exam.slot_booking_end_date:
        flash('Cancellation deadline has passed. You cannot cancel after the booking end date.', 'danger')
        return redirect(url_for('student.bookings'))

    booking.status = 'Cancelled'
    slot.sync_availability()
    db.session.commit()

    flash(f'Your booking for "{exam.examination_name}" has been cancelled.', 'info')
    return redirect(url_for('student.bookings'))

# ----------------- BOOKINGS HISTORY & RESULTS -----------------
@student_bp.route('/bookings')
@student_required
def bookings():
    bookings_list = Booking.query.filter_by(student_id=current_user.id).order_by(
        Booking.booking_date.desc()
    ).all()
    today = date.today()
    return render_template('student/bookings.html', bookings=bookings_list, today=today)

@student_bp.route('/scorecard/<int:booking_id>')
@student_required
def scorecard(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # Make sure only this student (or admin) can view this scorecard
    if booking.student_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access to scorecard.', 'danger')
        return redirect(url_for('student.bookings'))

    evaluation = booking.evaluation
    if not evaluation:
        flash('Results have not yet been evaluated/published for this examination.', 'warning')
        return redirect(url_for('student.bookings'))

    scores = evaluation.scores.all()
    return render_template('student/scorecard.html', booking=booking, evaluation=evaluation, scores=scores)

# ----------------- PROFILE -----------------
@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    student_prof = current_user.student_profile
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        department = request.form.get('department', '').strip()
        contact_details = request.form.get('contact_details', '').strip()

        if not full_name:
            flash('Full Name is required.', 'danger')
            return render_template('student/profile.html', student=student_prof)

        current_user.full_name = full_name
        if student_prof:
            student_prof.department = department
            student_prof.contact_details = contact_details
        db.session.commit()

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html', student=student_prof)
