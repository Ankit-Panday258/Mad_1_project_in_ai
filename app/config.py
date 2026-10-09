import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'emp-secret-key-mad1-secure-token-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(os.path.dirname(BASE_DIR), 'examination_portal.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
