from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from pathlib import Path  # Local import to avoid polluting module scope at import time

db = SQLAlchemy()
ma = Marshmallow()

def init_db(app):
    """Initialize the database with the Flask app."""
    # ------------------------------------------------------------------
    # Use an *absolute* path for the SQLite file so that the application
    # works no matter what the current working directory is.
    # ------------------------------------------------------------------

    # The project root is two levels up from this file (backend/app → backend → project root)
    project_root = Path(__file__).resolve().parent.parent.parent

    # Ensure the instance directory exists (otherwise SQLite cannot create the DB file)
    instance_dir = project_root / 'instance'
    instance_dir.mkdir(parents=True, exist_ok=True)

    db_path = instance_dir / 'finance.db'

    # Absolute path with three leading slashes for SQLAlchemy/SQLite URI
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.as_posix()}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    ma.init_app(app)
    
    with app.app_context():
        db.create_all()

def create_default_milestones():
    """Create default milestones if none exist."""
    # ------------------------------------------------------------------
    #  Rich default data: multiple scenarios / sub-scenarios, with goals &
    #  scenario-parameter values.  (Ported from the previous standalone script.)
    # ------------------------------------------------------------------

    from .models.milestone import Milestone
    from .models.scenario import Scenario
    from .models.sub_scenario import SubScenario
    from .models.goal import Goal
    from .models.scenario_parameter_value import ScenarioParameterValue

    if Milestone.query.first():  # already populated → skip
        return

    # Tiny helper ------------------------------------------------------
    def _get_or_create(model, defaults=None, **kwargs):
        obj = model.query.filter_by(**kwargs).one_or_none()
        if obj is None:
            params = {**kwargs, **(defaults or {})}
            obj = model(**params)  # type: ignore[arg-type]
            db.session.add(obj)
        else:
            if defaults:
                for k, v in (defaults or {}).items():
                    setattr(obj, k, v)
        return obj

    DEFAULT_SCENARIOS = [
        {"name": "Base Scenario", "subs": ["2 Kids", "3 Kids"]},
        {"name": "Good Scenario", "subs": ["2 Kids", "3 Kids"]},
    ]

    # ------------------------------------------------------------------
    #  Baseline milestone templates – will be duplicated for every combo.
    # ------------------------------------------------------------------

    TEMPLATE_MILESTONES = [
        {
            name='Current Liquid Assets',
            age_at_occurrence=default_age,
            milestone_type='Asset',
            disbursement_type='Perpetuity',
            amount=30000,
            payment=5000,
            occurrence='Yearly',
            duration=None,
            rate_of_return=0.07,
            order=0,
            parent_milestone_id=current_lifestyle_parent.id,
        },
        {
            name='Current Debt',
            age_at_occurrence=default_age,
            milestone_type='Liability',
            disbursement_type='Fixed Duration',
            amount=35000,
            payment=500,
            occurrence='Monthly',
            duration=120,
            rate_of_return=0.07,
            order=1,
            parent_milestone_id=current_lifestyle_parent.id
        },
        {
            name='Current Salary (incl. Bonus, Side Hustle, etc.)',
            age_at_occurrence=default_age,
            milestone_type='Income',
            disbursement_type='Fixed Duration',
            amount=50000,
            occurrence='Yearly',
            # duration=70 - default_age,
            duration=None,  # explicit duration omitted – will be dynamic
            duration_end_at_milestone="Retirement",
            rate_of_return=0.02,
            order=2,
            parent_milestone_id=current_lifestyle_parent.id
        },
        {
            name='Current Average Expenses',
            age_at_occurrence=default_age,
            milestone_type='Expense',
            disbursement_type='Fixed Duration',
            amount=3000,
            occurrence='Monthly',
            # duration=70 - default_age,
            duration=None,
            duration_end_at_milestone="Retirement",
            rate_of_return=0.03,
            order=3,
            parent_milestone_id=current_lifestyle_parent.id
        },
        {
            name='Retirement',
            age_at_occurrence=70,
            milestone_type='Expense',
            disbursement_type='Fixed Duration',
            amount=60000,
            occurrence='Yearly',
            # duration=30,
            duration=None,
            duration_end_at_milestone="Inheritance",
            rate_of_return=0.06,
            order=4,
            parent_milestone_id=retirement_parent.id,
            goal_parameters: ["age_at_occurrence"],
        },
        {
            name='Long Term Care (self)',
            age_at_occurrence=96,
            milestone_type='Expense',
            disbursement_type='Fixed Duration',
            amount=6000,
            occurrence='Monthly',
            duration=48,
            rate_of_return=0.04,
            order=5,
            parent_milestone_id=long_term_care_parent.id
        },
        {
            name='Inheritance',
            age_at_occurrence=100,
            milestone_type='Expense',
            disbursement_type='Fixed Duration',
            amount=10000,
            occurrence='Monthly',
            duration=1,
            rate_of_return=0.0,
            order=6,
            parent_milestone_id=inheritance_parent.id
        },
    ]

    # ------------------------------------------------------------------
    #  Optional per-scenario / sub-scenario overrides.
    #
    #  Structure:
    #      { (scenario_name, sub_name): { milestone_name: {param: value, ...}} }
    #
    #  Only the specified parameters are overridden – everything else falls
    #  back to the template above.
    # ------------------------------------------------------------------

    PARAM_OVERRIDES: dict[tuple[str, str], dict[str, dict[str, object]]] = {
        ("Base Scenario", "2 Kids"): {
            "Current Average Expenses": {"amount": 3_000},
        },
        ("Base Scenario", "3 Kids"): {
            "Current Average Expenses": {"amount": 5_000},
        },
        ("Good Scenario", "2 Kids"): {
            "Current Average Expenses": {"amount": 3_000},
        },
        ("Good Scenario", "3 Kids"): {
            "Current Average Expenses": {"amount": 5_000},
        },
    }
    
    # ------------------------------------------------------------------
    #  Insert
    # ------------------------------------------------------------------
    for scen_spec in DEFAULT_SCENARIOS:
        scen = _get_or_create(Scenario, parameters={}, name=scen_spec["name"])
        db.session.flush()

        for sub_name in scen_spec["subs"]:
            sub = _get_or_create(SubScenario, scenario_id=scen.id, name=sub_name)
            db.session.flush()

            for tpl in TEMPLATE_MILESTONES:
                # Apply per-scenario overrides --------------------------------
                overrides = PARAM_OVERRIDES.get((scen.name, sub.name), {}).get(tpl["name"], {})

                merged = {**tpl, **overrides}

                m_defaults = {k: v for k, v in merged.items() if k not in ("goal_parameters", "scenario_values")}
                m = _get_or_create(
                    Milestone,
                    **m_defaults,
                    scenario_id=scen.id,
                    scenario_name=scen.name,
                    sub_scenario_id=sub.id,
                    sub_scenario_name=sub.name,
                )
                db.session.flush()

                for param in merged.get("goal_parameters", []):
                    _get_or_create(Goal, milestone_id=m.id, parameter=param)

                for param, vals in merged.get("scenario_values", {}).items():
                    for v in vals:
                        _get_or_create(ScenarioParameterValue, milestone_id=m.id, parameter=param, value=v)

    db.session.commit() 