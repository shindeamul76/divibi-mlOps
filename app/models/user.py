# app/models/user.py
from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.auth.utils import generate_jwt_token

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='Viewer')  # Admin, Developer, Viewer
    is_active = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<User {self.username}>'

    # Check user role
    def has_role(self, role):
        return self.role == role

    # Set the password for the user
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Verify the password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Generate JWT token for the user
    def generate_auth_token(self):
        return generate_jwt_token(self.id, self.role)
