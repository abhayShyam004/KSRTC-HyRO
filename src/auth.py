"""
Authentication module for KSRTC-HyRO Admin Panel
Implements JWT-based authentication with bcrypt password hashing
"""
import os
import jwt
import bcrypt
import datetime
from functools import wraps
from flask import request, jsonify

# Secret key for JWT - use environment variable in production
JWT_SECRET = os.environ.get('JWT_SECRET', 'ksrtc-hyro-secret-key-2024-vitbp')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Token valid for 24 hours

# Admin credentials - hashed password
ADMIN_USERNAME = 'admin'
# Pre-hashed password for 'vitbp'
ADMIN_PASSWORD_HASH = bcrypt.hashpw('vitbp'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_token(username, role='admin'):
    """Generate a JWT token for authenticated user"""
    payload = {
        'sub': username,
        'role': role,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    """
    Decode and verify a JWT token
    Returns payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def login(username, password):
    """
    Authenticate user and return token if valid
    Returns (token, error_message)
    """
    # Check against hardcoded admin credentials
    if username == ADMIN_USERNAME:
        if verify_password(password, ADMIN_PASSWORD_HASH):
            token = generate_token(username, 'super_admin')
            return token, None
        else:
            return None, 'Invalid password'
    
    return None, 'User not found'

def token_required(f):
    """
    Decorator to protect routes that require authentication
    Checks for valid JWT in Authorization header or cookie
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check Authorization header first (Bearer token)
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        # Fallback to cookie
        if not token:
            token = request.cookies.get('admin_token')
        
        # Fallback to query parameter (for testing)
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NO_TOKEN'
            }), 401
        
        # Verify token
        payload = decode_token(token)
        if not payload:
            return jsonify({
                'error': 'Invalid or expired token',
                'code': 'INVALID_TOKEN'
            }), 401
        
        # Add user info to request context
        request.current_user = payload
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator for routes that require admin role
    Must be used after @token_required
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        role = request.current_user.get('role', '')
        if role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated


# ========== AUTH ROUTES (to be added to Flask app) ==========
def register_auth_routes(app):
    """Register authentication routes with Flask app"""
    
    @app.route('/api/auth/login', methods=['POST'])
    def auth_login():
        """Login endpoint - returns JWT token"""
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        token, error = login(username, password)
        
        if error:
            return jsonify({'error': error}), 401
        
        response = jsonify({
            'success': True,
            'token': token,
            'user': {
                'username': username,
                'role': 'super_admin'
            },
            'expires_in': JWT_EXPIRATION_HOURS * 3600  # seconds
        })
        
        # Also set as HttpOnly cookie for extra security
        response.set_cookie(
            'admin_token',
            token,
            httponly=True,
            secure=True,  # Only send over HTTPS
            samesite='Strict',
            max_age=JWT_EXPIRATION_HOURS * 3600
        )
        
        return response
    
    @app.route('/api/auth/logout', methods=['POST'])
    def auth_logout():
        """Logout endpoint - clears token cookie"""
        response = jsonify({'success': True})
        response.delete_cookie('admin_token')
        return response
    
    @app.route('/api/auth/verify', methods=['GET'])
    def auth_verify():
        """Verify if current token is valid"""
        token = None
        
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            token = request.cookies.get('admin_token')
        
        if not token:
            return jsonify({'valid': False, 'error': 'No token'}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({'valid': False, 'error': 'Invalid or expired token'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'username': payload.get('sub'),
                'role': payload.get('role')
            }
        })
