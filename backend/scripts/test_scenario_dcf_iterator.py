import pytest

from .scenario_dcf_iterator import ScenarioDCFIterator
from .db_connector import DBConnector
from backend.app.models.dcf import DCF


@pytest.fixture(scope="module")
def seeded_session():
    """Run the iterator once and return a fresh session for assertions."""
    # Execute the iterator – this should populate the `dcf` table
    ScenarioDCFIterator().run()

    # Return a new session for read-only assertions
    db = DBConnector()
    return db.get_session()


def test_dcf_table_not_empty(seeded_session):
    """At least one projection row must exist after running the iterator."""
    row_count = seeded_session.query(DCF).count()
    assert row_count > 0, "The DCF table is still empty – iterator failed to write rows."


def test_unique_projection_constraint(seeded_session):
    """The table should honour the (scenario_id, sub_scenario_id, age) uniqueness."""
    duplicates = (
        seeded_session.query(DCF.scenario_id, DCF.sub_scenario_id, DCF.age)
        .group_by(DCF.scenario_id, DCF.sub_scenario_id, DCF.age)
        .having(pytest.importorskip("sqlalchemy").func.count() > 1)
        .all()
    )
    assert not duplicates, "Duplicate projection rows were found in the DCF table."


def test_projection_covers_age_range(seeded_session):
    """For every scenario/sub-scenario all ages from min→max milestone age must be present."""
    # Pull min/max ages from milestones for each combo
    db = DBConnector()
    session = db.get_session()
    milestones = session.query(pytest.importorskip("backend.app.models.milestone").Milestone).all()

    combo_to_age_range = {}
    for m in milestones:
        key = (m.scenario_id, m.sub_scenario_id)
        combo_to_age_range.setdefault(key, [m.age_at_occurrence, m.age_at_occurrence])
        combo_to_age_range[key][0] = min(combo_to_age_range[key][0], m.age_at_occurrence)
        combo_to_age_range[key][1] = max(combo_to_age_range[key][1], m.age_at_occurrence)

    for (scenario_id, sub_scenario_id), (min_age, max_age) in combo_to_age_range.items():
        ages_in_dcf = {
            age for (age,) in seeded_session.query(DCF.age)
            .filter_by(scenario_id=scenario_id, sub_scenario_id=sub_scenario_id)
            .all()
        }
        expected_ages = set(range(min_age, max_age + 1))
        missing = expected_ages.difference(ages_in_dcf)
        assert not missing, (
            f"Projection for scenario {scenario_id}/{sub_scenario_id} is missing ages: {sorted(missing)}"
        )

