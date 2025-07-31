import itertools

import pytest

from backend.app.models.milestone import Milestone
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from backend.scripts.dcf_monte_carlo import simulate_milestones, MonteCarloSimulator
from backend.scripts.db_connector import DBConnector


# ---------------------------------------------------------------------------
#  Helpers for generating synthetic data
# ---------------------------------------------------------------------------

_id_gen = itertools.count(1)

def _next_id():
    return next(_id_gen)


def _sample_milestones() -> tuple[list[Milestone], ScenarioParameterValue]:
    """Return a minimal milestone scenario + one SPV to vary in tests."""

    milestones: list[Milestone] = []

    # Liquid assets baseline – rate_of_return will be varied by Monte Carlo
    liquid_assets = Milestone(
        name="Current Liquid Assets",
        milestone_type="Asset",
        age_at_occurrence=30,
        disbursement_type="Perpetuity",
        amount=50_000.0,
        rate_of_return=0.07,
        scenario_id=1,
        sub_scenario_id=1,
    )

    salary = Milestone(
        name="Current Salary",
        milestone_type="Income",
        age_at_occurrence=30,
        disbursement_type="Fixed Duration",
        amount=100_000.0,
        occurrence="Yearly",
        duration=35,  # ends at retirement
        rate_of_return=0.03,
        scenario_id=1,
        sub_scenario_id=1,
    )

    expenses = Milestone(
        name="Current Expenses",
        milestone_type="Expense",
        age_at_occurrence=30,
        disbursement_type="Fixed Duration",
        amount=40_000.0,
        occurrence="Yearly",
        duration=35,
        rate_of_return=0.02,
        scenario_id=1,
        sub_scenario_id=1,
    )

    # Manually assign IDs to mimic auto-increment behaviour
    liquid_assets.id = _next_id()
    salary.id = _next_id()
    expenses.id = _next_id()

    milestones.extend([liquid_assets, salary, expenses])

    spv = ScenarioParameterValue(
        milestone_id=liquid_assets.id,
        parameter="rate_of_return",
        value="0.07",
    )

    return milestones, spv

# ---------------------------------------------------------------------------
#  Unit-tests
# ---------------------------------------------------------------------------

def test_manual_simulation_basic():
    milestones, spv = _sample_milestones()
    (best_iter, best_df), (_, worst_df) = simulate_milestones(milestones, spv, iterations=200, sigma=0.05)

    best_ba = best_df.loc[best_df.Age == best_df.Age.max(), "Beginning Assets"].iloc[0]
    worst_ba = worst_df.loc[worst_df.Age == worst_df.Age.max(), "Beginning Assets"].iloc[0]

    # Best simulation should have >= BA than worst
    assert best_ba >= worst_ba

    # Both dataframes should cover at least 30 years of projection
    assert len(best_df) >= 30 and len(worst_df) >= 30


@pytest.mark.integration
def test_database_simulation_in_memory():
    # Use an in-memory SQLite DB so the test is completely isolated
    connector = DBConnector()
    connector.OVERRIDE_DATABASE_URI = "sqlite:///:memory:"

    # Create a session very early so the DB & tables are created *before* we add rows
    session = connector.get_session()

    # Manually insert synthetic milestones & SPV into the fresh DB
    milestones, spv = _sample_milestones()

    # SQLAlchemy models from app are already bound to the metadata, we can add them
    for m in milestones:
        session.add(m)
    session.add(spv)
    session.commit()

    # Run Monte Carlo with fewer iterations for speed
    sim = MonteCarloSimulator(iterations=20, debug=False)
    # Monkey-patch connector in simulator to reuse our in-memory DB
    sim.db_connector = connector
    sim.read_session = session
    sim.write_session = session

    sim.run()

    # Verify that rows were written
    from backend.app.models.monte_carlo_dcf import MonteCarloDCF

    max_rows = session.query(MonteCarloDCF).filter_by(result_type="max").all()
    min_rows = session.query(MonteCarloDCF).filter_by(result_type="min").all()

    assert len(max_rows) > 0 and len(min_rows) > 0

    # All rows should correspond to our scenario/sub-scenario ids
    for row in max_rows + min_rows:
        assert row.scenario_id == 1 and row.sub_scenario_id == 1
        assert row.scenario_parameter == "rate_of_return"

