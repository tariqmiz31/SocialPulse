"""Admin blueprint package"""
from flask import Blueprint, current_app
from flask_mail import Mail

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
mail = None

def init_mail(mail_instance: Mail):
    """Initialize mail instance for admin blueprint"""
    global mail
    mail = mail_instance

from . import roles  # noqa
