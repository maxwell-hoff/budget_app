"""default_data_loader.py
Create a standardised set of scenarios / sub-scenarios together with
milestones, goals and scenario-parameter values so that developers can
quickly reset the database to a known state for manual QA or automated
tests.

Run:
    python -m backend.scripts.default_data_loader  # uses default data set

The script is *idempotent*: running it multiple times will NOT create
duplicate rows – existing records are updated in-place.
"""
from __future__ import annotations

from typing import List, Dict
from backend.app import create_app
from backend.app.database import db
from backend.app.models.scenario import Scenario
from backend.app.models.sub_scenario import SubScenario
from backend.app.models.milestone import Milestone
from backend.app.models.goal import Goal
from backend.app.models.scenario_parameter_value import ScenarioParameterValue

# ---------------------------------------------------------------------------
#  Helper tiny ORM utilities
# ---------------------------------------------------------------------------

def _get_or_create(model, defaults: dict | None = None, **kwargs):
    obj = model.query.filter_by(**kwargs).one_or_none()
    if obj is None:
        params = {**kwargs, **(defaults or {})}
        obj = model(**params)  # type: ignore[arg-type]
        db.session.add(obj)
    else:
        # Update mutable columns from *defaults*
        if defaults:
            for k, v in defaults.items():
                setattr(obj, k, v)
    return obj

# ---------------------------------------------------------------------------
#  Default data description (can easily be customised)
# ---------------------------------------------------------------------------

DEFAULT_SCENARIOS: List[Dict] = [
    {
        "name": "Base Scenario",
        "sub_scenarios": ["2 Kids", "3 Kids"],
    },
    {
        "name": "Good Scenario",
        "sub_scenarios": ["2 Kids", "3 Kids"],
    },
]

# Milestone templates – will be *duplicated* for every (scenario, sub-scenario)
# pair.  Feel free to change the numbers as you like – they represent **annual**
# figures unless noted otherwise.
DEFAULT_MILESTONES: List[Dict] = [
    # Opening balances / flows at age 30
    # Split former 'Current Liquid Assets' into four buckets with distinct ROIs
    {"name": "Savings",  "age_at_occurrence": 30, "milestone_type": "Asset", "disbursement_type": "Perpetuity", "amount": 7_500,  "rate_of_return": 0.02, "goal_parameters": ["amount"]},
    {"name": "Checking", "age_at_occurrence": 30, "milestone_type": "Asset", "disbursement_type": "Perpetuity", "amount": 7_500,  "rate_of_return": 0.01, "goal_parameters": ["amount"]},
    {"name": "Stocks",   "age_at_occurrence": 30, "milestone_type": "Asset", "disbursement_type": "Perpetuity", "amount": 7_500,  "rate_of_return": 0.07, "goal_parameters": ["amount"]},
    {"name": "Bonds",    "age_at_occurrence": 30, "milestone_type": "Asset", "disbursement_type": "Perpetuity", "amount": 7_500,  "rate_of_return": 0.03, "goal_parameters": ["amount"]},
    {
        "name": "Current Debt",
        "age_at_occurrence": 30,
        "milestone_type": "Liability",
        "disbursement_type": "Fixed Duration",
        "amount": 35_000,
        "payment": 500,  # monthly
        "occurrence": "Monthly",
        "duration": 120,  # months
        "rate_of_return": 0.07,
        "goal_parameters": ["payment"],
        "scenario_values": {"payment": ["300", "800"]},
    },
    {
        "name": "Current Salary (incl. Bonus, Side Hustle, etc.)",
        "age_at_occurrence": 30,
        "milestone_type": "Income",
        "disbursement_type": "Fixed Duration",
        "amount": 50_000,
        "duration": 1,
        "occurrence": "Yearly",
        "rate_of_return": 0.02,
        "goal_parameters": ["amount"],
    },
    {
        "name": "Current Average Expenses",
        "age_at_occurrence": 30,
        "milestone_type": "Expense",
        "disbursement_type": "Fixed Duration",
        "amount": 3_000,          # monthly
        "occurrence": "Monthly",
        "duration": 1,
        "rate_of_return": 0.03,
        "goal_parameters": ["amount"],
    },
]

# ---------------------------------------------------------------------------
#  Main loader
# ---------------------------------------------------------------------------

def populate_defaults():
    for scen_spec in DEFAULT_SCENARIOS:
        scen = _get_or_create(Scenario, parameters={}, name=scen_spec["name"])
        db.session.flush()  # ensure ID is available

        for sub_name in scen_spec["sub_scenarios"]:
            sub = _get_or_create(SubScenario, scenario_id=scen.id, name=sub_name)
            db.session.flush()

            # ------------------------------------------------------------------
            # Populate milestones for this (scenario, sub-scenario) combo
            # ------------------------------------------------------------------
            for tpl in DEFAULT_MILESTONES:
                m_defaults = {k: v for k, v in tpl.items() if k not in ("goal_parameters", "scenario_values")}
                m = _get_or_create(
                    Milestone,
                    **m_defaults,
                    scenario_id=scen.id,
                    scenario_name=scen.name,
                    sub_scenario_id=sub.id,
                    sub_scenario_name=sub.name,
                )
                db.session.flush()

                # Mark goal parameters ----------------------------------------
                for param in tpl.get("goal_parameters", []):
                    _get_or_create(Goal, milestone_id=m.id, parameter=param)

                # Scenario parameter values -----------------------------------
                for param, val_list in tpl.get("scenario_values", {}).items():
                    for val in val_list:
                        _get_or_create(ScenarioParameterValue, milestone_id=m.id, parameter=param, value=val)

    db.session.commit()


# ---------------------------------------------------------------------------
#  CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        populate_defaults()
        print("Default scenarios, sub-scenarios and milestones inserted successfully.") 