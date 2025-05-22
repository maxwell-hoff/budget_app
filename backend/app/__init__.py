from flask import Flask, render_template
from flask_cors import CORS
from .database import init_db, create_default_milestones
from .models.milestone import Milestone
from .models.user import User
from .models.net_worth import MilestoneValueByAge, NetWorthByAge
from .models.scenario import Scenario
from .models.goal import Goal
from .models.scenario_parameter_value import ScenarioParameterValue
from .api.routes import api_bp
from .routes.scenarios import scenarios_bp
from .routes.net_worth import net_worth_bp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__,
                static_folder='../../frontend/static',
                template_folder='../../frontend/templates')
    CORS(app)
    
    # Initialize database
    init_db(app)
    
    # Create default milestones
    with app.app_context():
        create_default_milestones()
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(scenarios_bp)
    app.register_blueprint(net_worth_bp)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app 