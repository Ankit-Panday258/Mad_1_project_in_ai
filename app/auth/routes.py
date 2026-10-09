from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ..models import db, User, ExaminerProfile, StudentProfile

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_examiner:
            return redirect(url_for('examiner.dashboard'))
        elif current_user.is_student:
            return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        
        if not identifier or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('auth/login.html')

        # Find user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('auth/login.html')

        # Check examiner approval status
        if user.is_examiner:
            profile = user.examiner_profile
            if not profile or profile.status == 'pending':
                flash('Your examiner registration is pending Admin approval. Please wait for confirmation.', 'warning')
                return render_template('auth/login.html')
            elif profile.status in ['deactivated', 'rejected']:
                flash('Your examiner account is currently inactive. Please contact the administrator.', 'danger')
                return render_template('auth/login.html')

        login_user(user)
        flash(f'Welcome back, {user.full_name}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.is_examiner:
            return redirect(url_for('examiner.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        roll_no = request.form.get('roll_no', '').strip()
        department = request.form.get('department', '').strip()
        contact_details = request.form.get('contact_details', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not all([full_name, username, email, roll_no, department, password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register_student.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_student.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_student.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register_student.html')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please login or use another email.', 'danger')
            return render_template('auth/register_student.html')

        if StudentProfile.query.filter_by(roll_no=roll_no).first():
            flash('A student with this Roll Number is already registered.', 'danger')
            return render_template('auth/register_student.html')

        # Create student user and profile
        student_user = User(
            username=username,
            email=email,
            role='student',
            full_name=full_name
        )
        student_user.set_password(password)
        db.session.add(student_user)
        db.session.flush()

        profile = StudentProfile(
            user_id=student_user.id,
            roll_no=roll_no,
            department=department,
            contact_details=contact_details
        )
        db.session.add(profile)
        db.session.commit()

        flash('Student registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html')


@auth_bp.route('/register/examiner', methods=['GET', 'POST'])
def register_examiner():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        designation = request.form.get('designation', '').strip()
        contact_details = request.form.get('contact_details', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not all([full_name, username, email, department, password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register_examiner.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_examiner.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_examiner.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register_examiner.html')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please login or use another email.', 'danger')
            return render_template('auth/register_examiner.html')

        # Create examiner user and profile with pending status
        examiner_user = User(
            username=username,
            email=email,
            role='examiner',
            full_name=full_name
        )
        examiner_user.set_password(password)
        db.session.add(examiner_user)
        db.session.flush()

        profile = ExaminerProfile(
            user_id=examiner_user.id,
            contact_details=contact_details,
            department=department,
            designation=designation or 'Examiner',
            status='pending'
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration submitted successfully! Your account requires approval from the Admin before you can log in.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_examiner.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
