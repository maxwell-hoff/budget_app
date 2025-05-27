from datetime import datetime
from ..database import db
from sqlalchemy import UniqueConstraint

class SolvedParameterValue(db.Model):
    """Machine-generated value that solves a chosen goal parameter while keeping the milestone's PV constant."""

    __tablename__ = 'solved_parameter_values'

    id = db.Column(db.Integer, primary_key=True)

    # Relationships / denormalised grouping columns
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=False)
    scenario_id = db.Column(db.Integer, nullable=False)
    sub_scenario_id = db.Column(db.Integer, nullable=False)

    # Metadata about the solve
    goal_parameter = db.Column(db.String(50), nullable=False)  # e.g. 'amount'
    scenario_parameter = db.Column(db.String(50), nullable=False)  # e.g. 'age_at_occurrence'
    scenario_value = db.Column(db.String(100), nullable=False)  # concrete value that was applied

    solved_value = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('milestone_id', 'goal_parameter', 'scenario_parameter', 'scenario_value',
                         name='uix_milestone_goal_scenario_value'),
    )

    milestone = db.relationship('Milestone', backref=db.backref('solved_values', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, milestone_id: int, scenario_id: int, sub_scenario_id: int,
                 goal_parameter: str, scenario_parameter: str, scenario_value: str, solved_value: float):
        self.milestone_id = milestone_id
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        self.goal_parameter = goal_parameter
        self.scenario_parameter = scenario_parameter
        self.scenario_value = scenario_value
        self.solved_value = solved_value

    def to_dict(self):
        return {
            'id': self.id,
            'milestone_id': self.milestone_id,
            'scenario_id': self.scenario_id,
            'sub_scenario_id': self.sub_scenario_id,
            'goal_parameter': self.goal_parameter,
            'scenario_parameter': self.scenario_parameter,
            'scenario_value': self.scenario_value,
            'solved_value': self.solved_value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 