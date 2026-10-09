import unittest
from datetime import date, timedelta, time
from app import create_app
from app.models import db, User, Course, Examination, ExaminationSlot, Booking, ExaminationRubric

class TestExaminationManagementPortal(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def login(self, username, password):
        return self.client.post('/auth/login', data={
            'identifier': username,
            'password': password
        }, follow_redirects=True)

    def test_01_homepage_and_public_routes(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Examination Management Portal', response.data)

    def test_02_admin_login_and_dashboard(self):
        response = self.login('admin', 'admin123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Administrator Dashboard', response.data)
        self.assertIn(b'Courses', response.data)

    def test_03_pending_examiner_login_blocked(self):
        response = self.login('pending_examiner', 'examiner123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pending Admin approval', response.data)

    def test_04_approved_examiner_login(self):
        response = self.login('examiner1', 'examiner123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Examiner Portal', response.data)
        self.assertIn(b'My Created Slots', response.data)

    def test_05_student_login_and_dashboard(self):
        response = self.login('student1', 'student123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student Portal', response.data)
        self.assertIn(b'My Booked Examination Slots', response.data)

    def test_06_student_scorecard_view(self):
        self.login('student1', 'student123')
        with self.app.app_context():
            student = User.query.filter_by(username='student1').first()
            booking = Booking.query.filter_by(student_id=student.id).first()
            booking_id = booking.id

        response = self.client.get(f'/student/scorecard/{booking_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'EXAMINATION MANAGEMENT PORTAL', response.data)
        self.assertIn(b'OFFICIAL PERFORMANCE SCORECARD', response.data)

    def test_07_prevent_duplicate_booking(self):
        self.login('student1', 'student123')
        with self.app.app_context():
            # Find an available slot for exam1 (where student1 already has a booking)
            exam1 = Examination.query.filter_by(examination_name='MAD-1 Term Project Viva Voce').first()
            available_slot = ExaminationSlot.query.filter_by(examination_id=exam1.id, status='Available').first()
            slot_id = available_slot.id

        response = self.client.post(f'/student/slots/{slot_id}/book', follow_redirects=True)
        self.assertIn(b'Duplicate booking is prohibited', response.data)

    def test_08_api_endpoints_return_json(self):
        response = self.client.get('/api/courses')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

        response = self.client.get('/api/examinations')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertIn('total_courses', data)
        self.assertIn('total_examinations', data)

    def test_09_examiner_cannot_evaluate_other_examiner_student(self):
        # Examiner 2 logs in
        self.login('examiner2', 'examiner123')
        with self.app.app_context():
            # Booking 1 belongs to slot 1 whose examiner is examiner 1 (Dr. Rajesh Kumar)
            booking1 = Booking.query.first()
            b_id = booking1.id

        # Attempt to access evaluate route of booking 1
        response = self.client.get(f'/examiner/bookings/{b_id}/evaluate', follow_redirects=True)
        self.assertIn(b'Security policy: You can only evaluate students booked in your own slots', response.data)

if __name__ == '__main__':
    unittest.main()
