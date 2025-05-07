from datetime import datetime
from ..database import db

class Scenario(db.Model):
    """Model representing a saved scenario of parameters."""
    __tablename__ = 'scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    parameters = db.Column(db.JSON, nullable=False)  # Store all parameters as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters
        
    def to_dict(self):
        """Convert scenario to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 