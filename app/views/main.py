from flask import Blueprint, jsonify
bp = Blueprint('main', __name__)

@bp.get('/')
def index():
    return "<h1>Проект StudyPlanner запущен!</h1>"

@bp.get('/health/')
def health():
    return jsonify(status='ok', service='StudyPlanner')