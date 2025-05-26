from datetime import datetime
from ..database import db

class SubScenario(db.Model):
    """Model representing a sub-scenario that belongs to a parent scenario."""
    __tablename__ = 'sub_scenarios'

    id = db.Column(db.Integer, primary_key=True)
    # Reference back to the parent Scenario (identified by scenario_id on Milestone)
    scenario_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, scenario_id: int, name: str):
        self.scenario_id = scenario_id
        self.name = name

    def to_dict(self):
        """Serialize the SubScenario instance to a dict."""
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 