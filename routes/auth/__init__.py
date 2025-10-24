from flask import Blueprint

# Define the blueprint
auth = Blueprint("auth", __name__)

# IMPORTANT: import route modules so their @auth.route(...) decorators run
from . import login, register  # noqa: F401
