import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from .extensions import db
from .models import User

api_bp = Blueprint('api', __name__)

# Секретный ключ для токенов (в реальном проекте хранить в .env)
SECRET_KEY = "studyplanner_super_secret_key"

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({"error": "Unauthorized", "message": "Требуется токен"}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Unauthorized", "message": "Токен истек"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized", "message": "Неверный токен"}), 401
            
        return f(current_user, *args, **kwargs)
    return decorator

# ЭНДПОИНТ РЕГИСТРАЦИИ (POST /api/auth/register)
@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Bad Request", "message": "Email и пароль обязательны"}), 400
    
    if len(data['password']) < 6:
        return jsonify({"error": "Unprocessable Entity", "message": "Пароль слишком короткий (мин. 6 символов)"}), 422
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Unprocessable Entity", "message": "Email уже занят"}), 422
    
    user = User(username=data.get('username', 'User'), email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": "Пользователь создан", "id": user.id}), 201

# ЭНДПОИНТ АВТОРИЗАЦИИ (POST /api/auth/login)
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Bad Request", "message": "Email и пароль обязательны"}), 400
        
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Unauthorized", "message": "Неверный email или пароль"}), 401
        
    token = generate_token(user.id)
    return jsonify({"token": token, "role": user.role}), 200

# ЗАЩИЩЕННЫЙ ЭНДПОИНТ (GET /api/profile) - только для своих
@api_bp.route('/profile', methods=['GET'])
@token_required
def api_profile(current_user):
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }), 200