import os
from datetime import datetime, date, time, timedelta
from app import create_app
from app.models import (
    db, User, ExaminerProfile, StudentProfile,
    Course, Examination, ExaminationRubric, ExaminationSlot,
    Booking, Evaluation, EvaluationScore
)

def init_and_seed_database():
    app = create_app()
    with app.app_context():
        # Programmatic database table creation
        print("Dropping existing tables and recreating database programmatically...")
        db.drop_all()
        db.create_all()
        print("Database schema created successfully via SQLAlchemy model code.")

        # 1. Seed Pre-existing Administrator (Superuser)
        print("Seeding Administrator...")
        admin = User(
            username='admin',
            email='admin@university.edu',
            role='admin',
            full_name='System Administrator'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # 2. Seed Examiners
        print("Seeding Examiners...")
        # Examiner 1 (Approved)
        ex1 = User(
            username='examiner1',
            email='rajesh.kumar@university.edu',
            role='examiner',
            full_name='Dr. Rajesh Kumar'
        )
        ex1.set_password('examiner123')
        db.session.add(ex1)
        db.session.flush()
        db.session.add(ExaminerProfile(
            user_id=ex1.id,
            department='Computer Science & Engineering',
            designation='Associate Professor',
            contact_details='+91 98765 43210',
            status='approved'
        ))

        # Examiner 2 (Approved)
        ex2 = User(
            username='examiner2',
            email='sunita.rao@university.edu',
            role='examiner',
            full_name='Dr. Sunita Rao'
        )
        ex2.set_password('examiner123')
        db.session.add(ex2)
        db.session.flush()
        db.session.add(ExaminerProfile(
            user_id=ex2.id,
            department='Information Technology',
            designation='Professor',
            contact_details='+91 98111 22334',
            status='approved'
        ))

        # Examiner 3 (Approved)
        ex3 = User(
            username='examiner3',
            email='arvind.swami@university.edu',
            role='examiner',
            full_name='Prof. Arvind Swaminathan'
        )
        ex3.set_password('examiner123')
        db.session.add(ex3)
        db.session.flush()
        db.session.add(ExaminerProfile(
            user_id=ex3.id,
            department='Data Science & AI',
            designation='Assistant Professor',
            contact_details='+91 97222 33445',
            status='approved'
        ))

        # Examiner 4 (Pending approval for testing Admin approve/reject feature)
        ex4 = User(
            username='pending_examiner',
            email='vikram.singhania@university.edu',
            role='examiner',
            full_name='Dr. Vikram Singhania'
        )
        ex4.set_password('examiner123')
        db.session.add(ex4)
        db.session.flush()
        db.session.add(ExaminerProfile(
            user_id=ex4.id,
            department='Electrical Engineering',
            designation='Visiting Faculty',
            contact_details='+91 95555 66778',
            status='pending'
        ))

        # 3. Seed Students
        print("Seeding Students...")
        students_data = [
            ('student1', 'aarav.patel@student.edu', 'Aarav Patel', 'CS2026-001', 'Computer Science'),
            ('student2', 'priya.nair@student.edu', 'Priya Nair', 'CS2026-002', 'Computer Science'),
            ('student3', 'rohan.gupta@student.edu', 'Rohan Gupta', 'IT2026-015', 'Information Technology'),
            ('student4', 'sneha.mukherjee@student.edu', 'Sneha Mukherjee', 'AI2026-008', 'Data Science & AI')
        ]
        created_students = []
        for username, email, full_name, roll_no, dept in students_data:
            st = User(
                username=username,
                email=email,
                role='student',
                full_name=full_name
            )
            st.set_password('student123')
            db.session.add(st)
            db.session.flush()
            db.session.add(StudentProfile(
                user_id=st.id,
                roll_no=roll_no,
                department=dept,
                contact_details='+91 90000 12345'
            ))
            created_students.append(st)

        # 4. Seed Courses
        print("Seeding Courses...")
        c1 = Course(
            course_code='MAD101',
            course_name='Modern Application Development I',
            description='Core course covering Flask, Jinja2, SQLite, and responsive Bootstrap frontends.',
            status='active'
        )
        c2 = Course(
            course_code='SE301',
            course_name='Software Engineering & System Architecture',
            description='Design patterns, architectural decoupling, API design and verification.',
            status='active'
        )
        c3 = Course(
            course_code='BD201',
            course_name='Big Data Systems & Engineering',
            description='Scalable database architectures, query pipelines, and data storage design.',
            status='active'
        )
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        # 5. Seed Examinations with realistic dates
        print("Seeding Examinations...")
        today = date.today()
        exam1 = Examination(
            course_id=c1.id,
            examination_name='MAD-1 Term Project Viva Voce',
            examination_type='Viva',
            duration=30,
            max_marks=50.0,
            slot_creation_start_date=today - timedelta(days=10),
            slot_creation_end_date=today + timedelta(days=15),
            slot_booking_start_date=today - timedelta(days=5),
            slot_booking_end_date=today + timedelta(days=10),
            status='Booking Open'
        )

        exam2 = Examination(
            course_id=c1.id,
            examination_name='MAD-1 Practical Programming Assessment',
            examination_type='Practical',
            duration=60,
            max_marks=100.0,
            slot_creation_start_date=today - timedelta(days=2),
            slot_creation_end_date=today + timedelta(days=12),
            slot_booking_start_date=today + timedelta(days=13),
            slot_booking_end_date=today + timedelta(days=25),
            status='Slot Creation'
        )

        exam3 = Examination(
            course_id=c2.id,
            examination_name='Software Architecture Project Demonstration',
            examination_type='Project Demo',
            duration=45,
            max_marks=100.0,
            slot_creation_start_date=today - timedelta(days=8),
            slot_creation_end_date=today + timedelta(days=10),
            slot_booking_start_date=today - timedelta(days=3),
            slot_booking_end_date=today + timedelta(days=12),
            status='Booking Open'
        )

        exam4 = Examination(
            course_id=c3.id,
            examination_name='Big Data Query Optimization Lab Exam',
            examination_type='Assessment',
            duration=45,
            max_marks=50.0,
            slot_creation_start_date=today + timedelta(days=5),
            slot_creation_end_date=today + timedelta(days=20),
            slot_booking_start_date=today + timedelta(days=21),
            slot_booking_end_date=today + timedelta(days=30),
            status='Draft'
        )
        db.session.add_all([exam1, exam2, exam3, exam4])
        db.session.flush()

        # 6. Seed Rubrics
        print("Seeding Examination Rubrics...")
        # Rubrics for Exam 1 (MAD-1 Viva Voce, max 50)
        r1 = ExaminationRubric(
            examination_id=exam1.id,
            criterion_name='Backend Architecture & Flask Routes',
            max_marks=15.0,
            weightage=30.0,
            description='Demonstration of blueprints, request handling, error routes, and model interactions.'
        )
        r2 = ExaminationRubric(
            examination_id=exam1.id,
            criterion_name='Database Design & Integrity',
            max_marks=15.0,
            weightage=30.0,
            description='Relational schema consistency, foreign key cascades, and programmatic table creation.'
        )
        r3 = ExaminationRubric(
            examination_id=exam1.id,
            criterion_name='Live Viva & Code Demonstration',
            max_marks=20.0,
            weightage=40.0,
            description='Ability to answer examiner technical questions and demonstrate functional workflows.'
        )

        # Rubrics for Exam 3 (Project Demo, max 100)
        r4 = ExaminationRubric(
            examination_id=exam3.id,
            criterion_name='System Architecture & Decoupling',
            max_marks=30.0,
            weightage=30.0,
            description='Appropriate modularization, service patterns, and role boundaries.'
        )
        r5 = ExaminationRubric(
            examination_id=exam3.id,
            criterion_name='Security & Role-Based Access Control',
            max_marks=35.0,
            weightage=35.0,
            description='Strict authentication checks, role wrappers, and authorization safeguards.'
        )
        r6 = ExaminationRubric(
            examination_id=exam3.id,
            criterion_name='Live Demonstration & Edge-case Handling',
            max_marks=35.0,
            weightage=35.0,
            description='Verification of business constraints, overbooking guards, and conflict prevention.'
        )
        db.session.add_all([r1, r2, r3, r4, r5, r6])
        db.session.flush()

        # 7. Seed Examination Slots
        print("Seeding Examination Slots...")
        slot1 = ExaminationSlot(
            examination_id=exam1.id,
            examiner_id=ex1.id,
            slot_date=today + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(10, 30),
            max_capacity=1,
            available_seats=0, # Will be booked by student1
            status='Full',
            location_or_link='Lab 301, Computing Complex'
        )

        slot2 = ExaminationSlot(
            examination_id=exam1.id,
            examiner_id=ex1.id,
            slot_date=today + timedelta(days=2),
            start_time=time(11, 0),
            end_time=time(11, 30),
            max_capacity=1,
            available_seats=1,
            status='Available',
            location_or_link='Lab 301, Computing Complex'
        )

        slot3 = ExaminationSlot(
            examination_id=exam1.id,
            examiner_id=ex2.id,
            slot_date=today + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(14, 30),
            max_capacity=2,
            available_seats=1, # Will be booked by student2
            status='Available',
            location_or_link='https://meet.google.com/emp-viva-room1'
        )

        slot4 = ExaminationSlot(
            examination_id=exam3.id,
            examiner_id=ex3.id,
            slot_date=today + timedelta(days=4),
            start_time=time(15, 0),
            end_time=time(15, 45),
            max_capacity=3,
            available_seats=3,
            status='Available',
            location_or_link='Conference Room A'
        )

        db.session.add_all([slot1, slot2, slot3, slot4])
        db.session.flush()

        # 8. Seed Bookings
        print("Seeding Bookings & Evaluations...")
        # Booking 1: student1 in slot1 (Completed & Evaluated)
        b1 = Booking(
            student_id=created_students[0].id,
            slot_id=slot1.id,
            booking_date=datetime.utcnow() - timedelta(days=2),
            status='Completed'
        )
        db.session.add(b1)
        db.session.flush()

        # Evaluation for student1
        eval1 = Evaluation(
            booking_id=b1.id,
            examiner_id=ex1.id,
            total_marks_awarded=46.5,
            remarks='Outstanding conceptual clarity, clean modular architecture, and excellent explanation during live viva.',
            evaluated_at=datetime.utcnow() - timedelta(hours=5),
            status='Submitted'
        )
        db.session.add(eval1)
        db.session.flush()

        # Rubric scores for eval1
        es1 = EvaluationScore(evaluation_id=eval1.id, rubric_id=r1.id, marks_awarded=14.5, remarks='Well-structured blueprints')
        es2 = EvaluationScore(evaluation_id=eval1.id, rubric_id=r2.id, marks_awarded=14.0, remarks='Accurate schema design')
        es3 = EvaluationScore(evaluation_id=eval1.id, rubric_id=r3.id, marks_awarded=18.0, remarks='Confident viva responses')
        db.session.add_all([es1, es2, es3])

        # Booking 2: student2 in slot3 (Booked, awaiting viva)
        b2 = Booking(
            student_id=created_students[1].id,
            slot_id=slot3.id,
            booking_date=datetime.utcnow() - timedelta(days=1),
            status='Booked'
        )
        db.session.add(b2)

        # Commit all initial records
        db.session.commit()

        # Resynchronize slots
        slot1.sync_availability()
        slot2.sync_availability()
        slot3.sync_availability()
        slot4.sync_availability()
        db.session.commit()

        print("SUCCESS: Database initialized and seeded with complete sample records!")
        print("\nDemo Login Credentials:")
        print("1. Administrator:   Username: admin              Password: admin123")
        print("2. Examiner:        Username: examiner1          Password: examiner123")
        print("3. Student:         Username: student1           Password: student123")
        print("4. Pending Examiner:Username: pending_examiner   Password: examiner123")

if __name__ == '__main__':
    init_and_seed_database()
