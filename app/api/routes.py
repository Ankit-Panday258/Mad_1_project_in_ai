from flask import jsonify, request
from . import api_bp
from ..models import Course, Examination, ExaminationSlot, Booking, User, ExaminerProfile

@api_bp.route('/courses', methods=['GET'])
def get_courses():
    courses = Course.query.all()
    return jsonify([
        {
            'id': c.id,
            'course_code': c.course_code,
            'course_name': c.course_name,
            'description': c.description,
            'status': c.status
        } for c in courses
    ])

@api_bp.route('/examinations', methods=['GET'])
def get_examinations():
    status = request.args.get('status')
    query = Examination.query
    if status:
        query = query.filter_by(status=status)
    exams = query.all()
    return jsonify([
        {
            'id': e.id,
            'course_id': e.course_id,
            'course_code': e.course.course_code,
            'examination_name': e.examination_name,
            'examination_type': e.examination_type,
            'duration': e.duration,
            'max_marks': e.max_marks,
            'status': e.status,
            'slot_creation_window': {
                'start': str(e.slot_creation_start_date),
                'end': str(e.slot_creation_end_date)
            },
            'slot_booking_window': {
                'start': str(e.slot_booking_start_date),
                'end': str(e.slot_booking_end_date)
            }
        } for e in exams
    ])

@api_bp.route('/examinations/<int:exam_id>', methods=['GET'])
def get_examination_detail(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    return jsonify({
        'id': exam.id,
        'course_id': exam.course_id,
        'course_name': exam.course.course_name,
        'examination_name': exam.examination_name,
        'examination_type': exam.examination_type,
        'duration': exam.duration,
        'max_marks': exam.max_marks,
        'status': exam.status,
        'rubrics': [
            {
                'id': r.id,
                'criterion_name': r.criterion_name,
                'max_marks': r.max_marks,
                'weightage': r.weightage,
                'description': r.description
            } for r in exam.rubrics
        ]
    })

@api_bp.route('/examinations/<int:exam_id>/slots', methods=['GET'])
def get_examination_slots(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    slots = exam.slots.all()
    return jsonify([
        {
            'id': s.id,
            'examination_id': s.examination_id,
            'examiner_name': s.examiner.full_name,
            'date': str(s.slot_date),
            'start_time': str(s.start_time),
            'end_time': str(s.end_time),
            'max_capacity': s.max_capacity,
            'available_seats': s.available_seats,
            'status': s.status,
            'location_or_link': s.location_or_link
        } for s in slots
    ])

@api_bp.route('/examiners', methods=['GET'])
def get_examiners():
    status = request.args.get('status')
    query = User.query.filter_by(role='examiner').join(ExaminerProfile)
    if status:
        query = query.filter(ExaminerProfile.status == status)
    examiners = query.all()
    return jsonify([
        {
            'id': u.id,
            'full_name': u.full_name,
            'email': u.email,
            'department': u.examiner_profile.department if u.examiner_profile else None,
            'designation': u.examiner_profile.designation if u.examiner_profile else None,
            'status': u.examiner_profile.status if u.examiner_profile else 'unknown'
        } for u in examiners
    ])

@api_bp.route('/bookings', methods=['GET'])
def get_bookings():
    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return jsonify([
        {
            'id': b.id,
            'student_id': b.student_id,
            'student_name': b.student.full_name,
            'examination_id': b.slot.examination_id,
            'examination_name': b.slot.examination.examination_name,
            'slot_date': str(b.slot.slot_date),
            'slot_time': f"{b.slot.start_time.strftime('%H:%M')} - {b.slot.end_time.strftime('%H:%M')}",
            'status': b.status,
            'has_evaluation': b.evaluation is not None,
            'total_marks_awarded': b.evaluation.total_marks_awarded if b.evaluation else None
        } for b in bookings
    ])

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'total_courses': Course.query.count(),
        'total_examinations': Examination.query.count(),
        'total_examiners': User.query.filter_by(role='examiner').count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_slots': ExaminationSlot.query.count(),
        'total_bookings': Booking.query.count()
    })
