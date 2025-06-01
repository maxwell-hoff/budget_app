import pytest

from backend.app import create_app
from backend.app.database import db
from backend.app.models.solved_parameter_value import SolvedParameterValue
from backend.app.models.net_worth import MilestoneValueByAge
from backend.app.models.milestone import Milestone

# Import the helper module we want to test
from backend.scripts.scenario_calculations_template import (
    fetch_all_data,
    get_session,
    upsert_solved_parameter_values,
    upsert_milestone_values_by_age,
)


@pytest.fixture
def in_memory_app():
    """Create a throw-away Flask application backed by an in-memory SQLite DB."""
    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        # Clean up — remove the session/engine to not leak state between tests
        db.session.remove()


@pytest.fixture
def session(in_memory_app):
    """Return the SQLAlchemy session bound to the in-memory DB."""
    return db.session


def test_fetch_all_data_on_empty_db(session):
    data = fetch_all_data(session)
    assert data["milestones"] == []
    assert data["goals"] == []
    assert data["scenario_parameter_values"] == []
    assert data["milestone_values_by_age"] == []


def test_upsert_solved_parameter_values(session, dummy_milestone):
    record = {
        "milestone_id": dummy_milestone.id,
        "scenario_id": 1,
        "sub_scenario_id": 1,
        "goal_parameter": "amount",
        "scenario_parameter": "age_at_occurrence",
        "scenario_value": "35",
        "solved_value": 200_000.0,
    }

    # Insert
    upsert_solved_parameter_values(session, [record])
    assert session.query(SolvedParameterValue).count() == 1

    # Update (same unique key but different value)
    record["solved_value"] = 250_000.0
    upsert_solved_parameter_values(session, [record])
    assert session.query(SolvedParameterValue).one().solved_value == 250_000.0


def test_upsert_milestone_values_by_age(session, dummy_milestone):
    record = {"milestone_id": dummy_milestone.id, "age": 40, "value": 50_000.0}

    upsert_milestone_values_by_age(session, [record])
    assert session.query(MilestoneValueByAge).count() == 1

    # Update the same row
    record["value"] = 55_000.0
    upsert_milestone_values_by_age(session, [record])
    assert session.query(MilestoneValueByAge).one().value == 55_000.0


@pytest.fixture
def dummy_milestone(session):
    """Insert a single milestone so foreign-key constraints are satisfied."""
    ms = Milestone(
        name="Dummy",
        age_at_occurrence=30,
        milestone_type="Expense",
        amount=1_000.0,
    )
    session.add(ms)
    session.commit()
    return ms 