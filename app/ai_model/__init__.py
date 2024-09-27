from flask import Blueprint

bp = Blueprint('ai-model', __name__)

from app.ai_model import routes