import os
from flask import Flask, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from .models import db, User, School
from .routes.hoi import hoi_bp
from app.routes.exam import exam_bp  # Correct: looks inside the app package

migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configurations
    app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ream_matrix.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Subscription Enforcement Middleware
    @app.before_request
    def check_school_status():
        if request.endpoint and ('static' in request.endpoint or 'auth' in request.endpoint or 'super_admin' in request.endpoint):
            return
        
        if current_user.is_authenticated and current_user.role != 'super_admin' and current_user.school_id:
            school = School.query.get(current_user.school_id)
            if school and not school.is_active:
                flash('Your school account has been suspended due to non-payment. Please contact the system administrator.', 'danger')
                return redirect(url_for('auth.suspended'))

    # Register Blueprints
    from .routes.auth import auth_bp
    from .routes.school_admin import school_admin_bp
    from .routes.super_admin import super_admin_bp
    from .routes.ream_collection import ream_collection_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(school_admin_bp)
    app.register_blueprint(super_admin_bp)
    app.register_blueprint(ream_collection_bp)
    app.register_blueprint(hoi_bp)
    app.register_blueprint(exam_bp, url_prefix='/exam')
    
    return app