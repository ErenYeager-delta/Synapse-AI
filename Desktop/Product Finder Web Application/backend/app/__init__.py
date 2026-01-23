from flask import Flask, request
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from config import get_config

mongo = PyMongo()
jwt = JWTManager()

def create_app(config_name='default'):
    # Adjust paths to point to the frontend directory relative to this file (backend/app/__init__.py)
    app = Flask(__name__, 
                static_folder='../../frontend', 
                template_folder='../../frontend',
                static_url_path='')
    app.config.from_object(get_config(config_name))

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    mongo.init_app(app)
    jwt.init_app(app)

    @app.before_request
    def log_request_info():
        if request.path.startswith('/api'):
            print(f"API Request: {request.method} {request.path}")
            print(f"Headers: {dict(request.headers)}")

    # Register blueprints
    from app.routes import main
    from app.auth import auth
    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app
