from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import mongo
import bcrypt
from datetime import datetime

auth = Blueprint('auth', __name__)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

@auth.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Use 'customer' as default role
    role = data.get('role', 'customer').lower()
    if role not in ['customer', 'vendor', 'admin']:
        role = 'customer'
        
    # Check if user exists
    if mongo.db.users.find_one({"$or": [{"username": data['username']}, {"email": data['email']}]}):
        return jsonify({"error": "User already exists"}), 400
    
    new_user = {
        "username": data['username'],
        "email": data['email'],
        "password": hash_password(data['password']),
        "role": role,
        "created_at": datetime.utcnow()
    }
    
    # If role is vendor, create a vendor profile
    if role == 'vendor':
        vendor_id = mongo.db.vendors.insert_one({
            "name": data.get('vendor_name', data['username']),
            "email": data['email'],
            "rating": 0,
            "rating_count": "0"
        }).inserted_id
        new_user['vendor_id'] = vendor_id
    
    mongo.db.users.insert_one(new_user)
    return jsonify({"message": "User registered successfully"}), 201

@auth.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing credentials"}), 400
        
    user = mongo.db.users.find_one({"username": data['username']})
    
    if user and check_password(user['password'], data['password']):
        access_token = create_access_token(identity=str(user['_id']))
        
        return jsonify({
            "access_token": access_token,
            "role": user['role'],
            "username": user['username'],
            "vendor_id": str(user.get('vendor_id', ''))
        }), 200
        
    return jsonify({"error": "Invalid username or password"}), 401

@auth.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    identity = get_jwt_identity()
    return jsonify(identity), 200
