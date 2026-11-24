from app import create_app
from app.extensions import db
from app.models import User  

app = create_app()

with app.app_context():
    db.create_all()
    
    user = User.query.filter_by(email='howdyhoplala@mail.ru').first()
    if user:
        user.role = 'admin'
        db.session.commit()
        print(f'Пользователь {user.email} теперь АДМИН!')
    

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)