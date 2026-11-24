from flask import Flask, render_template
from config import Config
from .extensions import db, login_manager, mail, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)  
    
    from .routes import main
    app.register_blueprint(main)
    
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403
    
    return app