import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from .extensions import db, mail
from .models import User, PasswordResetToken, AIMessage
from .forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from .agent_client import ask_agent, AgentError

main = Blueprint('main', __name__)

# ДЕКОРАТОР ДЛЯ ПРОВЕРКИ РОЛИ АДМИНИСТРАТОРА
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна. Войдите.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы вошли.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.profile'))
        flash('Неверный email или пароль.', 'danger')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли.', 'info')
    return redirect(url_for('main.login'))

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            raw_token = secrets.token_urlsafe(32)
            hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
            
            PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).update({'is_used': True})
            
            new_token = PasswordResetToken(
                user_id=user.id,
                token_hash=hashed_token,
                expires_at=datetime.utcnow() + timedelta(minutes=30)
            )
            db.session.add(new_token)
            db.session.commit()
            
            reset_url = url_for('main.reset_password', token=raw_token, _external=True)
            msg = Message('Восстановление пароля', recipients=[user.email])
            msg.body = f'Для сброса пароля перейдите по ссылке: {reset_url}'
            
            try:
                mail.send(msg)
                print(f"\n=== ССЫЛКА ДЛЯ СБРОСА ПАРОЛЯ: {reset_url} ===\n")
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")
                flash('Произошла ошибка при отправке письма. Попробуйте позже.', 'danger')
                return redirect(url_for('main.forgot_password'))
            
        flash('Если аккаунт с таким email существует, письмо отправлено.', 'info')
        return redirect(url_for('main.login'))
    return render_template('forgot_password.html', form=form)

@main.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(token_hash=hashed_token, is_used=False).first()
    
    if not reset_token or not reset_token.is_valid():
        flash('Ссылка недействительна или истек её срок действия.', 'danger')
        return redirect(url_for('main.login'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = reset_token.user
        user.set_password(form.password.data)
        reset_token.is_used = True
        db.session.commit()
        flash('Пароль успешно изменён. Войдите.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html', form=form)

# ЗАЩИЩЕННЫЙ МАРШРУТ ДЛЯ АДМИНИСТРАТОРА
@main.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return "Панель администратора. Здесь вы можете управлять пользователями."

@main.route('/agent')
@login_required
def agent_page():
    return render_template('agent.html')

@main.route('/agent/send', methods=['POST'])
@login_required
def agent_send():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({"error": "Bad Request", "message": "Пустое сообщение"}), 400
    
    user_text = data['message'].strip()
    if len(user_text) > 1000:
        return jsonify({"error": "Bad Request", "message": "Слишком длинное сообщение"}), 400
        
    history_db = AIMessage.query.filter_by(user_id=current_user.id).order_by(AIMessage.created_at.asc()).all()
    history = [{"role": msg.role, "content": msg.content} for msg in history_db]
    
    try:
        answer = ask_agent(history, user_text)
    except AgentError as e:
        return jsonify({"error": "Service Unavailable", "message": str(e)}), 503
        
    user_msg = AIMessage(user_id=current_user.id, role='user', content=user_text)
    bot_msg = AIMessage(user_id=current_user.id, role='assistant', content=answer)
    db.session.add_all([user_msg, bot_msg])
    db.session.commit()
    
    return jsonify({"reply": answer}), 200