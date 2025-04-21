from flask import Flask, render_template
from flask_cors import CORS
from .database import init_db

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__,
                static_folder='../../frontend/static',
                template_folder='../../frontend/templates')
    CORS(app)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    from .api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app 