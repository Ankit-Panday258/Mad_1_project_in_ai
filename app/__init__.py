from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from .config import Config
from .models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .examiner.routes import examiner_bp
    from .student.routes import student_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(examiner_bp, url_prefix='/examiner')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            elif current_user.is_examiner:
                return redirect(url_for('examiner.dashboard'))
            elif current_user.is_student:
                return redirect(url_for('student.dashboard'))
        return render_template('home.html')

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('base.html', error_code=403, error_message="Access forbidden. You do not have permission for this resource."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('base.html', error_code=404, error_message="Page or resource not found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('base.html', error_code=500, error_message="Internal server error."), 500

    return app
