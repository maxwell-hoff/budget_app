from datetime import datetime
from ..database import db

class SolvedDCF(db.Model):
    """DCF rows calculated by dcf_solver for scenario-param sweeps."""

    __tablename__ = 'solved_dcf'

    id = db.Column(db.Integer, primary_key=True)

    # Scenario grouping --------------------------------------------------
    scenario_id = db.Column(db.Integer, nullable=False)
    sub_scenario_id = db.Column(db.Integer, nullable=False)

    # Solver metadata ----------------------------------------------------
    goal_parameter = db.Column(db.String(50), nullable=False)
    scenario_parameter = db.Column(db.String(50), nullable=False)
    scenario_value = db.Column(db.String(100), nullable=False)

    # Projection axis ----------------------------------------------------
    age = db.Column(db.Integer, nullable=False)

    # Cash-flow columns (same names as in dcf.py) ------------------------
    beginning_assets = db.Column(db.Float, nullable=False)
    assets_income = db.Column(db.Float, nullable=False)
    beginning_liabilities = db.Column(db.Float, nullable=False)
    liabilities_expense = db.Column(db.Float, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    expenses = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Ensure uniqueness for the solver dimensions + age row
        db.UniqueConstraint(
            'scenario_id', 'sub_scenario_id', 'goal_parameter',
            'scenario_parameter', 'scenario_value', 'age',
            name='uq_solved_dcf_projection'
        ),
    )

    def __init__(self, *, scenario_id: int, sub_scenario_id: int,
                 goal_parameter: str, scenario_parameter: str, scenario_value: str,
                 age: int, beginning_assets: float, assets_income: float,
                 beginning_liabilities: float, liabilities_expense: float,
                 salary: float, expenses: float):
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        self.goal_parameter = goal_parameter
        self.scenario_parameter = scenario_parameter
        self.scenario_value = scenario_value
        self.age = age
        self.beginning_assets = beginning_assets
        self.assets_income = assets_income
        self.beginning_liabilities = beginning_liabilities
        self.liabilities_expense = liabilities_expense
        self.salary = salary
        self.expenses = expenses 