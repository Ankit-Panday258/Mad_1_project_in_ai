from flask import Blueprint

examiner_bp = Blueprint('examiner', __name__)

from . import routes
