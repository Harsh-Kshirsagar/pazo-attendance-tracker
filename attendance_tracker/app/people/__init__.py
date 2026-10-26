from flask import Blueprint

bp = Blueprint("people", __name__, url_prefix="/people")

from . import routes  # noqa: E402,F401
