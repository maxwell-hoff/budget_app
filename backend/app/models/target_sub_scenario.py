from datetime import datetime

from ..database import db


class TargetSubScenario(db.Model):
    """One (scenario_id → sub_scenario_id) mapping marking the *anchor* sub-scenario.

    Only a single row is allowed per scenario_id (enforced by a UNIQUE constraint).
    """

    __tablename__ = 'target_sub_scenarios'

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id'), unique=True, nullable=False)
    sub_scenario_id = db.Column(db.Integer, db.ForeignKey('sub_scenarios.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'sub_scenario_id': self.sub_scenario_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        } 