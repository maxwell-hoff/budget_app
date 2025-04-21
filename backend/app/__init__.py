from flask import Flask
from flask_cors import CORS
from .database import init_db

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    from .api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app 