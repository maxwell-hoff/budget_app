from datetime import datetime
from ..database import db

class DCF(db.Model):
    """Model representing a discounted-cash-flow projection row."""
    __tablename__ = 'dcf'

    id = db.Column(db.Integer, primary_key=True)

    # Partitioning keys
    scenario_id = db.Column(db.Integer, nullable=False)
    sub_scenario_id = db.Column(db.Integer, nullable=False)

    # Projection axis
    age = db.Column(db.Integer, nullable=False)

    # Cash-flow columns – use snake_case field names so that they map 1:1 to DataFrame columns
    beginning_assets = db.Column(db.Float, nullable=False)
    assets_income = db.Column(db.Float, nullable=False)
    beginning_liabilities = db.Column(db.Float, nullable=False)
    liabilities_expense = db.Column(db.Float, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    expenses = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('scenario_id', 'sub_scenario_id', 'age', name='uq_dcf_projection'),
    )

    def __init__(self, *, scenario_id: int, sub_scenario_id: int, age: int, beginning_assets: float,
                 assets_income: float, beginning_liabilities: float, liabilities_expense: float,
                 salary: float, expenses: float):
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        self.age = age
        self.beginning_assets = beginning_assets
        self.assets_income = assets_income
        self.beginning_liabilities = beginning_liabilities
        self.liabilities_expense = liabilities_expense
        self.salary = salary
        self.expenses = expenses

    def to_dict(self):
        """Return a serialisable dict of the row (helpful for JSON responses/tests)."""
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'sub_scenario_id': self.sub_scenario_id,
            'age': self.age,
            'beginning_assets': self.beginning_assets,
            'assets_income': self.assets_income,
            'beginning_liabilities': self.beginning_liabilities,
            'liabilities_expense': self.liabilities_expense,
            'salary': self.salary,
            'expenses': self.expenses,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        } 