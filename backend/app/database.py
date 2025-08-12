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
        # Ensure *all* model classes are imported so their tables are present
        # in SQLAlchemy metadata before we call ``create_all``.  Omitting an
        # import here means the corresponding table will NOT be created and
        # subsequent queries will raise "no such table" errors.

        from .models import (
            user,  # noqa: F401 – imported for side-effect
            milestone,  # includes ParentMilestone
            scenario,
            sub_scenario,
            goal,
            scenario_parameter_value,
            dcf,
            net_worth,
            solved_dcf,
            solved_parameter_value,
            target_sub_scenario,
            monte_carlo_dcf,
        )

        db.create_all()

def create_default_milestones():
    """Create default milestones if none exist."""
    # ------------------------------------------------------------------
    #  Rich default data: multiple scenarios / sub-scenarios, with goals &
    #  scenario-parameter values.  (Ported from the previous standalone script.)
    # ------------------------------------------------------------------

    from .models.milestone import Milestone, ParentMilestone
    from .models.scenario import Scenario
    from .models.sub_scenario import SubScenario
    from .models.goal import Goal
    from .models.scenario_parameter_value import ScenarioParameterValue
    from .models.net_worth import MilestoneValueByAge

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

    PARENT_GROUPS = {
        "Current Lifestyle": (30, 70),
        "Retirement": (70, 100),
        "Long Term Care": (96, 100),
        "Inheritance": (100, 100),
    }

    # If there are existing milestones, run a one-off migration to split
    # 'Current Liquid Assets' into four buckets. Otherwise, insert defaults.
    from sqlalchemy import and_
    if Milestone.query.first():
        # Ensure parent groups exist (used for newly created bucket rows)
        # and build a name → id map for convenience.
        parent_map: dict[str, int] = {}
        for name, (min_age, max_age) in PARENT_GROUPS.items():
            p = _get_or_create(ParentMilestone, name=name, min_age=min_age, max_age=max_age)
            db.session.flush()
            parent_map[name] = p.id

        # For every (scenario, sub_scenario) convert the legacy row if present.
        legacy_rows = Milestone.query.filter(Milestone.name == 'Current Liquid Assets').all()

        # Proactively remove dependent milestone-values to avoid NOT NULL updates on flush
        legacy_ids = [row.id for row in legacy_rows]
        if legacy_ids:
            MilestoneValueByAge.query.filter(MilestoneValueByAge.milestone_id.in_(legacy_ids)).delete(synchronize_session=False)
            db.session.flush()

        for legacy in legacy_rows:
            # Skip when buckets already exist to keep idempotency
            with db.session.no_autoflush:
                existing_bucket = Milestone.query.filter(
                    and_(
                        Milestone.scenario_id == legacy.scenario_id,
                        Milestone.sub_scenario_id == legacy.sub_scenario_id,
                        Milestone.name.in_(['Savings', 'Checking', 'Stocks', 'Bonds'])
                    )
                ).first()
            if existing_bucket:
                # Safe to delete the legacy row to avoid double-counting
                db.session.delete(legacy)
                db.session.flush()
                continue

            total_amt = legacy.amount or 0.0
            split = total_amt / 4.0
            bucket_specs = [
                ("Savings", 0.02),
                ("Checking", 0.01),
                ("Stocks", 0.07),
                ("Bonds", 0.03),
            ]

            # Create four new asset milestones
            for idx, (nm, roi) in enumerate(bucket_specs):
                m = Milestone(
                    name=nm,
                    age_at_occurrence=legacy.age_at_occurrence,
                    milestone_type="Asset",
                    disbursement_type="Perpetuity",
                    amount=split,
                    rate_of_return=roi,
                    parent_milestone_id=parent_map.get("Current Lifestyle"),
                    order=idx,
                    scenario_id=legacy.scenario_id,
                    scenario_name=legacy.scenario_name,
                    sub_scenario_id=legacy.sub_scenario_id,
                    sub_scenario_name=legacy.sub_scenario_name,
                )
                db.session.add(m)

            # Remove the legacy row (its dependent values were cleared above)
            db.session.delete(legacy)
            db.session.flush()

        db.session.commit()
        return

    DEFAULT_SCENARIOS = [
        {"name": "Base Scenario", "subs": ["2 Kids", "3 Kids"]},
        {"name": "Good Scenario", "subs": ["2 Kids", "3 Kids"]},
    ]

    # ------------------------------------------------------------------
    #  Ensure parent milestone *groups* exist so child milestones can reference
    #  them via ``parent_milestone_id`` (used by the front-end to group rows).
    # ------------------------------------------------------------------

    parent_map: dict[str, int] = {}
    for name, (min_age, max_age) in PARENT_GROUPS.items():
        p = _get_or_create(ParentMilestone, name=name, min_age=min_age, max_age=max_age)
        db.session.flush()
        parent_map[name] = p.id

    # ------------------------------------------------------------------
    #  Baseline milestone templates – will be duplicated for every combo.
    # ------------------------------------------------------------------

    TEMPLATE_MILESTONES = [
        # Split former 'Current Liquid Assets' into four buckets
        {
            "name": "Savings",
            "age_at_occurrence": 30,
            "milestone_type": "Asset",
            "disbursement_type": "Perpetuity",
            "amount": 7_500,
            "rate_of_return": 0.02,
            "parent_group": "Current Lifestyle",
            "order": 0,
        },
        {
            "name": "Checking",
            "age_at_occurrence": 30,
            "milestone_type": "Asset",
            "disbursement_type": "Perpetuity",
            "amount": 7_500,
            "rate_of_return": 0.01,
            "parent_group": "Current Lifestyle",
            "order": 1,
        },
        {
            "name": "Stocks",
            "age_at_occurrence": 30,
            "milestone_type": "Asset",
            "disbursement_type": "Perpetuity",
            "amount": 7_500,
            "rate_of_return": 0.07,
            "parent_group": "Current Lifestyle",
            "order": 2,
        },
        {
            "name": "Bonds",
            "age_at_occurrence": 30,
            "milestone_type": "Asset",
            "disbursement_type": "Perpetuity",
            "amount": 7_500,
            "rate_of_return": 0.03,
            "parent_group": "Current Lifestyle",
            "order": 3,
        },
        {
            "name": "Current Debt",
            "age_at_occurrence": 30,
            "milestone_type": "Liability",
            "disbursement_type": "Fixed Duration",
            "amount": 35_000,
            "payment": 500,        # monthly
            "occurrence": "Monthly",
            "duration": 120,        # months
            "rate_of_return": 0.07,
            "parent_group": "Current Lifestyle",
            "order": 4,
        },
        {
            "name": "Current Salary (incl. Bonus, Side Hustle, etc.)",
            "age_at_occurrence": 30,
            "milestone_type": "Income",
            "disbursement_type": "Fixed Duration",
            "amount": 50_000,
            "occurrence": "Yearly",
            "duration": None,  # ends at retirement
            "duration_end_at_milestone": "Retirement",
            "rate_of_return": 0.02,
            "parent_group": "Current Lifestyle",
            "order": 5,
        },
        {
            "name": "Current Average Expenses",
            "age_at_occurrence": 30,
            "milestone_type": "Expense",
            "disbursement_type": "Fixed Duration",
            "amount": 3_000,        # monthly figure
            "occurrence": "Monthly",
            "duration": None,  # ends at retirement
            "duration_end_at_milestone": "Retirement",
            "rate_of_return": 0.03,
            "parent_group": "Current Lifestyle",
            "order": 6,
        },
        {
            "name": "Retirement",
            "age_at_occurrence": 65,  # fallback – real start is dynamic
            "milestone_type": "Expense",
            "disbursement_type": "Fixed Duration",
            "amount": 60_000, #* ((1 + 0.02) ** 40),  # store FV value
            "amount_value_type": "PV",  # default selection PV
            "occurrence": "Yearly",
            "duration": None,  # ends at inheritance
            "duration_end_at_milestone": "Inheritance",
            # "start_after_milestone": "Current Salary (incl. Bonus, Side Hustle, etc.)",
            "rate_of_return": 0.02,
            "goal_parameters": ["age_at_occurrence"],
            "parent_group": "Retirement",
            "order": 7,
        },
        {
            "name": "Long Term Care (self)",
            "age_at_occurrence": 96,
            "milestone_type": "Expense",
            "disbursement_type": "Fixed Duration",
            "amount": 6_000 * ((1 + 0.02) ** 66),
            "amount_value_type": "PV",
            "occurrence": "Monthly",
            "duration": 48,
            "rate_of_return": 0.02,
            "parent_group": "Long Term Care",
            "order": 8,
        },
        {
            "name": "Inheritance",
            "age_at_occurrence": 100,
            "milestone_type": "Expense",
            "disbursement_type": "Fixed Duration",
            "amount": 0,
            "occurrence": "Monthly",
            "duration": 1,
            "rate_of_return": 0.0,
            "parent_group": "Inheritance",
            "order": 9,
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
            "Current Salary (incl. Bonus, Side Hustle, etc.)": {"amount": 50_000},
        },
        ("Base Scenario", "3 Kids"): {
            "Current Average Expenses": {"amount": 5_000},
            "Current Salary (incl. Bonus, Side Hustle, etc.)": {"amount": 50_000},
        },
        ("Good Scenario", "2 Kids"): {
            "Current Average Expenses": {"amount": 3_000},
            "Current Salary (incl. Bonus, Side Hustle, etc.)": {"amount": 100_000},
        },
        ("Good Scenario", "3 Kids"): {
            "Current Average Expenses": {"amount": 5_000},
            "Current Salary (incl. Bonus, Side Hustle, etc.)": {"amount": 100_000},
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

            for idx, tpl in enumerate(TEMPLATE_MILESTONES):
                # Apply per-scenario overrides --------------------------------
                overrides = PARAM_OVERRIDES.get((scen.name, sub.name), {}).get(tpl["name"], {})

                merged = {**tpl, **overrides}

                # Fill default order when missing
                if 'order' not in merged:
                    merged['order'] = idx

                # Map parent_group → parent_milestone_id
                if 'parent_milestone_id' not in merged and merged.get('parent_group'):
                    merged['parent_milestone_id'] = parent_map.get(merged['parent_group'])

                m_defaults = {k: v for k, v in merged.items() if k not in ("goal_parameters", "scenario_values", "parent_group")}
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