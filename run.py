from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates database tables if they don't exist
        
        # Auto-create default Super Admin if none exists
        if not User.query.filter_by(role='super_admin').first():
            default_admin = User(
                username='superadmin',
                password_hash=generate_password_hash('superadmin123'),
                role='super_admin',
                school_id=None
            )
            db.session.add(default_admin)
            db.session.commit()
            print("Default Super Admin account created successfully.")

    app.run(debug=True)