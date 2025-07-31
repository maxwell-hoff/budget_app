from datetime import datetime

from ..database import db

class MonteCarloDCF(db.Model):
    """DCF rows coming from Monte Carlo simulation.

    For every Scenario → Sub-scenario → ScenarioParameterValue combination we
    keep the *best* and *worst* simulation paths according to the ending
    beginning-assets balance at age 100 (or the last simulated age when < 100).
    Each row describes one projection year.
    """

    __tablename__ = "monte_carlo_dcf"

    id = db.Column(db.Integer, primary_key=True)

    # Scenario grouping --------------------------------------------------
    scenario_id = db.Column(db.Integer, nullable=False)
    sub_scenario_id = db.Column(db.Integer, nullable=False)

    # Scenario parameter that was varied ---------------------------------
    scenario_parameter = db.Column(db.String(50), nullable=False)
    # *Mean* (baseline) parameter value – stored as text to mirror
    # ScenarioParameterValue.value.
    scenario_value = db.Column(db.String(100), nullable=False)

    # Classification of the simulation path ------------------------------
    # Either "max" (highest ending BA) or "min" (lowest ending BA)
    result_type = db.Column(db.String(3), nullable=False)

    # Projection axis ----------------------------------------------------
    age = db.Column(db.Integer, nullable=False)

    # Cash-flow columns (names match `dcf` / `solved_dcf`) ---------------
    beginning_assets = db.Column(db.Float, nullable=False)
    assets_income = db.Column(db.Float, nullable=False)
    beginning_liabilities = db.Column(db.Float, nullable=False)
    liabilities_expense = db.Column(db.Float, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    expenses = db.Column(db.Float, nullable=False)

    # Metadata -----------------------------------------------------------
    iteration = db.Column(db.Integer, nullable=False)  # which Monte Carlo draw produced this row
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        # Ensure uniqueness so we can perform idempotent upserts
        db.UniqueConstraint(
            "scenario_id",
            "sub_scenario_id",
            "scenario_parameter",
            "scenario_value",
            "result_type",
            "age",
            name="uq_monte_carlo_projection",
        ),
    )

    def __init__(
        self,
        *,
        scenario_id: int,
        sub_scenario_id: int,
        scenario_parameter: str,
        scenario_value: str,
        result_type: str,
        iteration: int,
        age: int,
        beginning_assets: float,
        assets_income: float,
        beginning_liabilities: float,
        liabilities_expense: float,
        salary: float,
        expenses: float,
    ):
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        self.scenario_parameter = scenario_parameter
        self.scenario_value = scenario_value
        self.result_type = result_type
        self.iteration = iteration
        self.age = age
        self.beginning_assets = beginning_assets
        self.assets_income = assets_income
        self.beginning_liabilities = beginning_liabilities
        self.liabilities_expense = liabilities_expense
        self.salary = salary
        self.expenses = expenses
