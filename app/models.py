from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'examiner', 'student'
    full_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 1-to-1 relationships
    examiner_profile = db.relationship('ExaminerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    # Relationships for foreign keys
    created_slots = db.relationship('ExaminationSlot', backref='examiner', lazy='dynamic')
    student_bookings = db.relationship('Booking', backref='student', lazy='dynamic')
    evaluations_given = db.relationship('Evaluation', backref='examiner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_examiner(self):
        return self.role == 'examiner'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_approved_examiner(self):
        if not self.is_examiner:
            return False
        return self.examiner_profile and self.examiner_profile.status == 'approved'


class ExaminerProfile(db.Model):
    __tablename__ = 'examiner_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    contact_details = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(120), nullable=False, default='General')
    designation = db.Column(db.String(120), nullable=True, default='Examiner')
    status = db.Column(db.String(20), nullable=False, default='pending') # 'pending', 'approved', 'rejected', 'deactivated'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    department = db.Column(db.String(120), nullable=False, default='Computer Science')
    contact_details = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    course_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active') # 'active', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    examinations = db.relationship('Examination', backref='course', cascade='all, delete-orphan', lazy='dynamic')


class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    examination_name = db.Column(db.String(150), nullable=False)
    examination_type = db.Column(db.String(50), nullable=False, default='Viva') # 'Viva', 'Practical', 'Project Demo', 'Assessment'
    duration = db.Column(db.Integer, nullable=False, default=30) # Duration in minutes
    max_marks = db.Column(db.Float, nullable=False, default=100.0)
    
    # Timelines
    slot_creation_start_date = db.Column(db.Date, nullable=False)
    slot_creation_end_date = db.Column(db.Date, nullable=False)
    slot_booking_start_date = db.Column(db.Date, nullable=False)
    slot_booking_end_date = db.Column(db.Date, nullable=False)
    
    # Status: 'Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed'
    status = db.Column(db.String(30), nullable=False, default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    rubrics = db.relationship('ExaminationRubric', backref='examination', cascade='all, delete-orphan', lazy='dynamic')
    slots = db.relationship('ExaminationSlot', backref='examination', cascade='all, delete-orphan', lazy='dynamic')

    def is_slot_creation_open(self):
        # Open if status explicitly says Slot Creation OR within date bounds when not draft/completed/closed
        if self.status == 'Slot Creation':
            return True
        if self.status in ['Draft', 'Closed', 'Completed']:
            return False
        today = date.today()
        return self.slot_creation_start_date <= today <= self.slot_creation_end_date

    def is_slot_booking_open(self):
        # Open if status explicitly says Booking Open OR within date bounds when not draft/closed/completed
        if self.status == 'Booking Open':
            return True
        if self.status in ['Draft', 'Slot Creation', 'Closed', 'Completed']:
            return False
        today = date.today()
        return self.slot_booking_start_date <= today <= self.slot_booking_end_date

    @property
    def total_rubric_marks(self):
        return sum([r.max_marks for r in self.rubrics])


class ExaminationRubric(db.Model):
    __tablename__ = 'examination_rubrics'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    criterion_name = db.Column(db.String(120), nullable=False)
    max_marks = db.Column(db.Float, nullable=False, default=10.0)
    weightage = db.Column(db.Float, nullable=False, default=100.0) # Percentage or weight
    description = db.Column(db.Text, nullable=True)

    scores = db.relationship('EvaluationScore', backref='rubric', cascade='all, delete-orphan', lazy='dynamic')


class ExaminationSlot(db.Model):
    __tablename__ = 'examination_slots'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=1)
    available_seats = db.Column(db.Integer, nullable=False, default=1)
    
    # Status: 'Available', 'Full', 'Cancelled', 'Completed'
    status = db.Column(db.String(20), nullable=False, default='Available')
    location_or_link = db.Column(db.String(255), nullable=True, default='Lab 101 / Online Link')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='slot', cascade='all, delete-orphan', lazy='dynamic')

    def sync_availability(self):
        active_bookings_count = self.bookings.filter(Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])).count()
        remaining = self.max_capacity - active_bookings_count
        self.available_seats = max(0, remaining)
        if self.available_seats == 0 and self.status == 'Available':
            self.status = 'Full'
        elif self.available_seats > 0 and self.status == 'Full':
            self.status = 'Available'

    @property
    def is_modifiable(self):
        # Examiners can update/remove slots before student booking starts for this slot (i.e. No active bookings)
        active_bookings_count = self.bookings.filter(Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])).count()
        return active_bookings_count == 0


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('examination_slots.id', ondelete='CASCADE'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status: 'Booked', 'Cancelled', 'Completed', 'Rescheduled'
    status = db.Column(db.String(20), nullable=False, default='Booked')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 1-to-1 Evaluation
    evaluation = db.relationship('Evaluation', backref='booking', uselist=False, cascade='all, delete-orphan')


class Evaluation(db.Model):
    __tablename__ = 'evaluations'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    total_marks_awarded = db.Column(db.Float, nullable=False, default=0.0)
    remarks = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='Submitted') # 'Submitted', 'Published'

    scores = db.relationship('EvaluationScore', backref='evaluation', cascade='all, delete-orphan', lazy='dynamic')


class EvaluationScore(db.Model):
    __tablename__ = 'evaluation_scores'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id', ondelete='CASCADE'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('examination_rubrics.id', ondelete='CASCADE'), nullable=False)
    marks_awarded = db.Column(db.Float, nullable=False, default=0.0)
    remarks = db.Column(db.String(255), nullable=True)
