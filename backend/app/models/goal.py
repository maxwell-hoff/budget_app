from datetime import datetime
from ..database import db

class Goal(db.Model):
    """Model representing a parameter that has been flagged as a goal for a given milestone."""
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=False)
    # Parameter name this goal refers to (e.g., 'amount', 'duration', ...)
    parameter = db.Column(db.String(50), nullable=False)
    # Whether this parameter is currently marked as a goal (toggleable from the UI)
    is_goal = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to Milestone is defined via backref so we don't need explicit attribute here.
    milestone = db.relationship('Milestone', backref=db.backref('goals', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, milestone_id: int, parameter: str, is_goal: bool = True):
        self.milestone_id = milestone_id
        self.parameter = parameter
        self.is_goal = is_goal

    def to_dict(self):
        """Convert goal to a dictionary representation."""
        return {
            'id': self.id,
            'milestone_id': self.milestone_id,
            'parameter': self.parameter,
            'is_goal': self.is_goal,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 