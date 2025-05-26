from datetime import datetime
from ..database import db
from sqlalchemy import UniqueConstraint

class ScenarioParameterValue(db.Model):
    """Parameter values captured for scenario analysis for a given milestone."""
    __tablename__ = 'scenario_parameter_values'

    id = db.Column(db.Integer, primary_key=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=False)
    parameter = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(100), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure we don't store duplicates for same milestone/parameter/value
    __table_args__ = (
        UniqueConstraint('milestone_id', 'parameter', 'value', name='uix_milestone_param_value'),
    )

    milestone = db.relationship('Milestone', backref=db.backref('scenario_values', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, milestone_id: int, parameter: str, value: str):
        self.milestone_id = milestone_id
        self.parameter = parameter
        self.value = value

    def to_dict(self):
        return {
            'id': self.id,
            'milestone_id': self.milestone_id,
            'parameter': self.parameter,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 