from datetime import datetime, date
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import admin_bp
from ..models import (
    db, User, ExaminerProfile, StudentProfile,
    Course, Examination, ExaminationRubric, ExaminationSlot, Booking, Evaluation
)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- ADMIN DASHBOARD -----------------
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_courses = Course.query.count()
    total_examinations = Examination.query.count()
    total_examiners = User.query.filter_by(role='examiner').count()
    total_students = User.query.filter_by(role='student').count()
    total_slots = ExaminationSlot.query.count()
    total_bookings = Booking.query.count()
    
    pending_examiners_count = ExaminerProfile.query.filter_by(status='pending').count()
    active_examinations = Examination.query.filter(Examination.status.in_(['Slot Creation', 'Booking Open'])).all()
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(8).all()
    
    stats = {
        'courses': total_courses,
        'examinations': total_examinations,
        'examiners': total_examiners,
        'students': total_students,
        'slots': total_slots,
        'bookings': total_bookings,
        'pending_examiners': pending_examiners_count
    }
    return render_template('admin/dashboard.html', stats=stats, active_examinations=active_examinations, recent_bookings=recent_bookings)

# ----------------- COURSES -----------------
@admin_bp.route('/courses')
@admin_required
def courses():
    search_q = request.args.get('q', '').strip()
    query = Course.query
    if search_q:
        query = query.filter(
            (Course.course_code.ilike(f'%{search_q}%')) |
            (Course.course_name.ilike(f'%{search_q}%'))
        )
    courses_list = query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses_list, search_q=search_q)

@admin_bp.route('/courses/create', methods=['GET', 'POST'])
@admin_required
def create_course():
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'active')

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'danger')
            return render_template('admin/course_form.html', action='Create', course=None)

        if Course.query.filter_by(course_code=course_code).first():
            flash(f'Course code "{course_code}" already exists.', 'danger')
            return render_template('admin/course_form.html', action='Create', course=None)

        new_course = Course(
            course_code=course_code,
            course_name=course_name,
            description=description,
            status=status
        )
        db.session.add(new_course)
        db.session.commit()
        flash(f'Course "{course_name}" created successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Create', course=None)

@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'active')

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        existing = Course.query.filter(Course.course_code == course_code, Course.id != course.id).first()
        if existing:
            flash(f'Course code "{course_code}" is already in use by another course.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        course.course_code = course_code
        course.course_name = course_name
        course.description = description
        course.status = status
        db.session.commit()

        flash('Course updated successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Edit', course=course)

@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    name = course.course_name
    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{name}" and all associated examinations were deleted.', 'info')
    return redirect(url_for('admin.courses'))

# ----------------- EXAMINATIONS -----------------
@admin_bp.route('/examinations')
@admin_required
def examinations():
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    query = Examination.query
    if search_q:
        query = query.filter(Examination.examination_name.ilike(f'%{search_q}%'))
    if status_filter:
        query = query.filter_by(status=status_filter)

    exams = query.order_by(Examination.created_at.desc()).all()
    courses_list = Course.query.filter_by(status='active').all()
    return render_template('admin/examinations.html', examinations=exams, courses=courses_list, search_q=search_q, status_filter=status_filter)

@admin_bp.route('/examinations/create', methods=['GET', 'POST'])
@admin_required
def create_examination():
    courses_list = Course.query.filter_by(status='active').all()
    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        exam_name = request.form.get('examination_name', '').strip()
        exam_type = request.form.get('examination_type', 'Viva')
        duration = request.form.get('duration', type=int) or 30
        max_marks = request.form.get('max_marks', type=float) or 100.0
        
        slot_cr_start = request.form.get('slot_creation_start_date')
        slot_cr_end = request.form.get('slot_creation_end_date')
        slot_bk_start = request.form.get('slot_booking_start_date')
        slot_bk_end = request.form.get('slot_booking_end_date')
        status = request.form.get('status', 'Draft')

        if not all([course_id, exam_name, slot_cr_start, slot_cr_end, slot_bk_start, slot_bk_end]):
            flash('All timeline dates and exam details are required.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses_list)

        try:
            d_cr_start = datetime.strptime(slot_cr_start, '%Y-%m-%d').date()
            d_cr_end = datetime.strptime(slot_cr_end, '%Y-%m-%d').date()
            d_bk_start = datetime.strptime(slot_bk_start, '%Y-%m-%d').date()
            d_bk_end = datetime.strptime(slot_bk_end, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format provided.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses_list)

        if d_cr_start > d_cr_end:
            flash('Slot creation start date cannot be after end date.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses_list)

        if d_bk_start > d_bk_end:
            flash('Slot booking start date cannot be after end date.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses_list)

        new_exam = Examination(
            course_id=course_id,
            examination_name=exam_name,
            examination_type=exam_type,
            duration=duration,
            max_marks=max_marks,
            slot_creation_start_date=d_cr_start,
            slot_creation_end_date=d_cr_end,
            slot_booking_start_date=d_bk_start,
            slot_booking_end_date=d_bk_end,
            status=status
        )
        db.session.add(new_exam)
        db.session.commit()
        flash(f'Examination "{exam_name}" created successfully.', 'success')
        return redirect(url_for('admin.examination_detail', exam_id=new_exam.id))

    return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses_list)

@admin_bp.route('/examinations/<int:exam_id>')
@admin_required
def examination_detail(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    rubrics = exam.rubrics.all()
    slots = exam.slots.all()
    bookings_count = Booking.query.join(ExaminationSlot).filter(ExaminationSlot.examination_id == exam.id).count()
    return render_template('admin/examination_detail.html', exam=exam, rubrics=rubrics, slots=slots, bookings_count=bookings_count)

@admin_bp.route('/examinations/<int:exam_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    courses_list = Course.query.filter_by(status='active').all()

    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        exam_name = request.form.get('examination_name', '').strip()
        exam_type = request.form.get('examination_type', 'Viva')
        duration = request.form.get('duration', type=int) or 30
        max_marks = request.form.get('max_marks', type=float) or 100.0
        
        slot_cr_start = request.form.get('slot_creation_start_date')
        slot_cr_end = request.form.get('slot_creation_end_date')
        slot_bk_start = request.form.get('slot_booking_start_date')
        slot_bk_end = request.form.get('slot_booking_end_date')
        status = request.form.get('status', exam.status)

        try:
            d_cr_start = datetime.strptime(slot_cr_start, '%Y-%m-%d').date()
            d_cr_end = datetime.strptime(slot_cr_end, '%Y-%m-%d').date()
            d_bk_start = datetime.strptime(slot_bk_start, '%Y-%m-%d').date()
            d_bk_end = datetime.strptime(slot_bk_end, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid date format provided.', 'danger')
            return render_template('admin/examination_form.html', action='Edit', exam=exam, courses=courses_list)

        exam.course_id = course_id
        exam.examination_name = exam_name
        exam.examination_type = exam_type
        exam.duration = duration
        exam.max_marks = max_marks
        exam.slot_creation_start_date = d_cr_start
        exam.slot_creation_end_date = d_cr_end
        exam.slot_booking_start_date = d_bk_start
        exam.slot_booking_end_date = d_bk_end
        exam.status = status
        db.session.commit()

        flash(f'Examination "{exam_name}" updated successfully.', 'success')
        return redirect(url_for('admin.examination_detail', exam_id=exam.id))

    return render_template('admin/examination_form.html', action='Edit', exam=exam, courses=courses_list)

@admin_bp.route('/examinations/<int:exam_id>/status', methods=['POST'])
@admin_required
def set_examination_status(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    new_status = request.form.get('status')
    if new_status in ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']:
        exam.status = new_status
        db.session.commit()
        flash(f'Examination status changed to "{new_status}".', 'success')
    return redirect(url_for('admin.examination_detail', exam_id=exam.id))

@admin_bp.route('/examinations/<int:exam_id>/delete', methods=['POST'])
@admin_required
def delete_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    name = exam.examination_name
    db.session.delete(exam)
    db.session.commit()
    flash(f'Examination "{name}" was deleted successfully.', 'info')
    return redirect(url_for('admin.examinations'))

# ----------------- RUBRICS -----------------
@admin_bp.route('/examinations/<int:exam_id>/rubrics', methods=['GET', 'POST'])
@admin_required
def manage_rubrics(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks = request.form.get('max_marks', type=float) or 10.0
        weightage = request.form.get('weightage', type=float) or 100.0
        description = request.form.get('description', '').strip()

        if not criterion_name:
            flash('Criterion name is required.', 'danger')
        else:
            rubric = ExaminationRubric(
                examination_id=exam.id,
                criterion_name=criterion_name,
                max_marks=max_marks,
                weightage=weightage,
                description=description
            )
            db.session.add(rubric)
            db.session.commit()
            flash(f'Rubric criterion "{criterion_name}" added.', 'success')
        return redirect(url_for('admin.manage_rubrics', exam_id=exam.id))

    rubrics = exam.rubrics.all()
    return render_template('admin/rubrics.html', exam=exam, rubrics=rubrics)

@admin_bp.route('/rubrics/<int:rubric_id>/delete', methods=['POST'])
@admin_required
def delete_rubric(rubric_id):
    rubric = ExaminationRubric.query.get_or_404(rubric_id)
    exam_id = rubric.examination_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion removed.', 'info')
    return redirect(url_for('admin.manage_rubrics', exam_id=exam_id))

# ----------------- EXAMINERS -----------------
@admin_bp.route('/examiners')
@admin_required
def examiners():
    status_filter = request.args.get('status', '')
    query = User.query.filter_by(role='examiner').join(ExaminerProfile)
    if status_filter:
        query = query.filter(ExaminerProfile.status == status_filter)
    
    examiner_users = query.all()
    return render_template('admin/examiners.html', examiners=examiner_users, status_filter=status_filter)

@admin_bp.route('/examiners/<int:user_id>/action', methods=['POST'])
@admin_required
def examiner_action(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_examiner or not user.examiner_profile:
        flash('Invalid examiner record.', 'danger')
        return redirect(url_for('admin.examiners'))

    action = request.form.get('action')
    if action == 'approve':
        user.examiner_profile.status = 'approved'
        flash(f'Examiner {user.full_name} has been approved.', 'success')
    elif action == 'reject':
        user.examiner_profile.status = 'rejected'
        flash(f'Examiner {user.full_name} request has been rejected.', 'warning')
    elif action == 'deactivate':
        user.examiner_profile.status = 'deactivated'
        flash(f'Examiner {user.full_name} account has been deactivated.', 'secondary')
    elif action == 'activate':
        user.examiner_profile.status = 'approved'
        flash(f'Examiner {user.full_name} account has been re-activated.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.examiners'))

# ----------------- SLOTS -----------------
@admin_bp.route('/slots')
@admin_required
def slots():
    exam_id = request.args.get('exam_id', type=int)
    examiner_id = request.args.get('examiner_id', type=int)
    query = ExaminationSlot.query
    if exam_id:
        query = query.filter_by(examination_id=exam_id)
    if examiner_id:
        query = query.filter_by(examiner_id=examiner_id)

    slots_list = query.order_by(ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.asc()).all()
    examinations = Examination.query.all()
    examiners = User.query.filter_by(role='examiner').all()
    return render_template('admin/slots.html', slots=slots_list, examinations=examinations, examiners=examiners, selected_exam=exam_id, selected_examiner=examiner_id)

@admin_bp.route('/slots/<int:slot_id>/reassign', methods=['GET', 'POST'])
@admin_required
def reassign_slot_examiner(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    approved_examiners = User.query.filter_by(role='examiner').join(ExaminerProfile).filter(ExaminerProfile.status == 'approved').all()

    if request.method == 'POST':
        new_examiner_id = request.form.get('new_examiner_id', type=int)
        new_examiner = User.query.get(new_examiner_id)
        if not new_examiner or not new_examiner.is_examiner:
            flash('Invalid examiner selected.', 'danger')
            return redirect(url_for('admin.reassign_slot_examiner', slot_id=slot.id))

        old_name = slot.examiner.full_name
        slot.examiner_id = new_examiner_id
        db.session.commit()
        flash(f'Slot reassigned from {old_name} to {new_examiner.full_name} successfully.', 'success')
        return redirect(url_for('admin.slots'))

    return render_template('admin/reassign_slot.html', slot=slot, examiners=approved_examiners)

# ----------------- BOOKINGS -----------------
@admin_bp.route('/bookings')
@admin_required
def bookings():
    status_filter = request.args.get('status', '')
    query = Booking.query.join(ExaminationSlot).join(Examination)
    if status_filter:
        query = query.filter(Booking.status == status_filter)

    bookings_list = query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings_list, status_filter=status_filter)

@admin_bp.route('/bookings/<int:booking_id>/reschedule', methods=['GET', 'POST'])
@admin_required
def reschedule_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    current_slot = booking.slot
    exam = current_slot.examination

    # Find available alternate slots for the SAME examination
    available_slots = ExaminationSlot.query.filter(
        ExaminationSlot.examination_id == exam.id,
        ExaminationSlot.id != current_slot.id,
        ExaminationSlot.status.in_(['Available'])
    ).all()

    if request.method == 'POST':
        new_slot_id = request.form.get('new_slot_id', type=int)
        new_slot = ExaminationSlot.query.get_or_404(new_slot_id)

        if new_slot.available_seats <= 0:
            flash('The chosen slot has no available capacity.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking.id))

        # Reassign slot
        booking.slot_id = new_slot.id
        booking.status = 'Rescheduled'
        
        # Sync seats for both slots
        current_slot.sync_availability()
        new_slot.sync_availability()
        db.session.commit()

        flash(f'Booking #{booking.id} for student {booking.student.full_name} successfully rescheduled to {new_slot.slot_date} ({new_slot.start_time.strftime("%H:%M")} - {new_slot.end_time.strftime("%H:%M")}).', 'success')
        return redirect(url_for('admin.bookings'))

    return render_template('admin/reschedule_booking.html', booking=booking, current_slot=current_slot, available_slots=available_slots)

# ----------------- UNIFIED SEARCH -----------------
@admin_bp.route('/search')
@admin_required
def search():
    q = request.args.get('q', '').strip()
    students = []
    examiners = []
    examinations = []
    bookings = []

    if q:
        # Search students
        students = User.query.filter_by(role='student').outerjoin(StudentProfile).filter(
            (User.username.ilike(f'%{q}%')) |
            (User.full_name.ilike(f'%{q}%')) |
            (User.email.ilike(f'%{q}%')) |
            (StudentProfile.roll_no.ilike(f'%{q}%'))
        ).all()

        # Search examiners
        examiners = User.query.filter_by(role='examiner').outerjoin(ExaminerProfile).filter(
            (User.username.ilike(f'%{q}%')) |
            (User.full_name.ilike(f'%{q}%')) |
            (User.email.ilike(f'%{q}%')) |
            (ExaminerProfile.department.ilike(f'%{q}%'))
        ).all()

        # Search examinations
        examinations = Examination.query.filter(
            (Examination.examination_name.ilike(f'%{q}%')) |
            (Examination.examination_type.ilike(f'%{q}%'))
        ).all()

        # Search bookings by ID or Student Name
        bookings_query = Booking.query.join(User, Booking.student_id == User.id)
        if q.isdigit():
            bookings = bookings_query.filter(
                (Booking.id == int(q)) |
                (User.full_name.ilike(f'%{q}%'))
            ).all()
        else:
            bookings = bookings_query.filter(User.full_name.ilike(f'%{q}%')).all()

    return render_template('admin/search.html', q=q, students=students, examiners=examiners, examinations=examinations, bookings=bookings)
