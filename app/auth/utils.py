# app/auth/utils.py
import jwt
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from functools import wraps

# Function to generate JWT token
def generate_jwt_token(user_id, role, expires_in=3600):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

# Function to decode JWT token
def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}

# Decorator to protect routes
def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is missing'}), 401
        
        try:
            token = auth_header.split()[1]  # Split "Bearer <token>"
            payload = decode_jwt_token(token)
            if 'error' in payload:
                return jsonify({'error': payload['error']}), 401
        except IndexError:
            return jsonify({'error': 'Token is missing or invalid'}), 401

        return f(*args, **kwargs)
    return decorated_function
