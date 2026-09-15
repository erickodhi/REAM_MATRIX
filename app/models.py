from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the SQLAlchemy extension
db = SQLAlchemy()

class School(db.Model):
    """Represents a registered institution (tenant) on the platform."""
    __tablename__ = 'school'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # True = Active, False = Suspended for non-payment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships to link data strictly to this school
    users = db.relationship('User', backref='school', lazy=True, cascade='all, delete-orphan')
    students = db.relationship('Student', backref='school', lazy=True, cascade='all, delete-orphan')
    forms = db.relationship('FormGrade', backref='school', lazy=True, cascade='all, delete-orphan')
    streams = db.relationship('Stream', backref='school', lazy=True, cascade='all, delete-orphan')
    settings = db.relationship('SchoolSetting', backref='school', uselist=False, cascade='all, delete-orphan')


class SchoolSetting(db.Model):
    """Tracks active term and academic year parameters for an institution."""
    __tablename__ = 'school_setting'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False, unique=True)
    current_term = db.Column(db.String(20), default='Term 1')      # 'Term 1', 'Term 2', or 'Term 3'
    current_academic_year = db.Column(db.String(20), default='2026') # e.g., '2026'

class FormGrade(db.Model):
    """Custom forms or grades created by the school (e.g., Form 1, Grade 9)."""
    __tablename__ = 'form_grade'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)


class Stream(db.Model):
    """Custom streams created by the school (e.g., East, North, Blue)."""
    __tablename__ = 'stream'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)



class User(db.Model, UserMixin):
    """Platform users including Super Admin and school-level staff."""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'super_admin', 'school_admin', 'hoi', 'ream_collection', 'exam_officer'
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    __tablename__ = 'student'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    admission_no = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    form_grade = db.Column(db.String(50), nullable=False)
    stream = db.Column(db.String(50), nullable=False)
    enrollment_term = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    term_1_status = db.Column(db.String(20), default='Pending')
    term_2_status = db.Column(db.String(20), default='Pending')
    term_3_status = db.Column(db.String(20), default='Pending')
    account_owed = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure admission number is unique per school PER academic year (allows multi-year history)
    __table_args__ = (
        db.UniqueConstraint('school_id', 'admission_no', 'academic_year', name='_school_adm_year_uc'),
    )

class ExamRequisition(db.Model):
    __tablename__ = 'exam_requisitions'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    
    department_subject = db.Column(db.String(150), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(150), nullable=False)
    form_grade = db.Column(db.String(50), nullable=False)
    num_students = db.Column(db.Integer, nullable=False)
    sheets_per_student = db.Column(db.Integer, nullable=False)
    
    padding_sheets = db.Column(db.Integer, default=100)
    total_sheets_required = db.Column(db.Integer, nullable=False)
    full_reams_to_issue = db.Column(db.Integer, nullable=False)
    leftover_loose_sheets = db.Column(db.Integer, nullable=False)
    
    sheets_returned = db.Column(db.Integer, default=0)
    
    # Add this new flag to track direct loose sheet disbursements:
    is_loose_disbursement = db.Column(db.Boolean, default=False)
    
    status = db.Column(db.String(20), default='Pending')
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)
    
    school = db.relationship('School', backref=db.backref('exam_requisitions', lazy=True))

class StoreCollection(db.Model):
    __tablename__ = 'store_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    
    sheets_added = db.Column(db.Integer, nullable=False)  # Total sheets or reams converted to sheets
    date_collected = db.Column(db.DateTime, default=datetime.utcnow)
    collected_by = db.Column(db.String(100), nullable=True)