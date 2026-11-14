from flask import Blueprint
bp = Blueprint('auth', __name__)

@bp.get('/login/')
def login():
    return 'Форма входа будет реализована позже'