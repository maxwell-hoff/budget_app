import math
import pytest
import itertools

from backend.app.models.milestone import Milestone
from backend.app.models.goal import Goal
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from .dcf_solver import DCFGoalSolver


@pytest.fixture(scope="module")
def sample_data():
    """Return a small milestone list + goal + scenario parameter for quick tests."""

    # Helper to generate sequential IDs (simulating DB auto-increment)
    _id_gen = itertools.count(1)
    def _next_id():
        return next(_id_gen)

    milestones = []

    def _new_ms(**kwargs):
        obj = Milestone(**kwargs)
        obj.id = _next_id()
        return obj

    milestones.extend([
        _new_ms(
            name="Current Salary",
            milestone_type="Income",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=110_000.0,
            occurrence="Yearly",
            duration=6,
            rate_of_return=0.04,
            scenario_id=1,
            sub_scenario_id=1,
        ),
        _new_ms(
            name="Current Expenses",
            milestone_type="Expense",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=60_000.0,
            occurrence="Yearly",
            duration=6,
            rate_of_return=0.02,
            scenario_id=1,
            sub_scenario_id=1,
        ),
        _new_ms(
            name="Current Debt",
            milestone_type="Liability",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=20_000.0,
            occurrence="Yearly",
            duration=4,
            rate_of_return=0.00,
            scenario_id=1,
            sub_scenario_id=1,
        ),
    ])

    # Simple liquid asset + salary + expense baseline (like earlier unit-tests)Milestone(
    liquid_assets = _new_ms(
        name="Current Liquid Assets",
        milestone_type="Asset",
        age_at_occurrence=30,
        disbursement_type="Perpetuity",
        amount=100_000.0,
        occurrence="Yearly",
        duration=None,
        rate_of_return=0.10,
        scenario_id=1,
        sub_scenario_id=1,
    )
    # Goal: solve for *amount* of a new retirement milestone so that BA@40 == BA baseline
    retirement = _new_ms(
        name="Retirement",
        milestone_type="Expense",
        age_at_occurrence=36,
        disbursement_type="Fixed Duration",
        amount=55_000.0,
        occurrence="Yearly",
        duration=5,
        rate_of_return=0.02,
        scenario_id=1,
        sub_scenario_id=1,
    )
    milestones.append(retirement)
    milestones.append(liquid_assets)

    goal = Goal(milestone_id=retirement.id, parameter="age_at_occurrence", is_goal=True)

    # Scenario parameter: shift rate of return to 15% instead of 10%
    spv = ScenarioParameterValue(milestone_id=liquid_assets.id, parameter="rate_of_return", value="0.08")

    return milestones, goal, spv


def test_goal_solver_converges(sample_data):
    milestones, goal, spv = sample_data

    # Build baseline BA
    from backend.scripts.dcf_calculator_manual import DCFModel
    baseline_ba = (
        DCFModel.from_milestones(milestones).run().as_frame().iloc[-1]["Beginning Assets"]
    )

    solver = DCFGoalSolver(milestones, baseline_ba)
    solved_val, solved_ms = solver.solve(goal, spv)

    solved_ba = (
        DCFModel.from_milestones(solved_ms).run().as_frame().iloc[-1]["Beginning Assets"]
    )
    solved_df = (
        DCFModel.from_milestones(solved_ms).run().as_frame()
    )
    # Fetch baseline value of the goal parameter before solving for clearer debug output
    baseline_param_val = next(m for m in milestones if m.id == goal.milestone_id).__dict__[goal.parameter]
    print(
        f'\nsolved_ba: {solved_ba}, baseline_ba: {baseline_ba}, '
        f'\nnsolved_val: {solved_val}, baseline_param_val: {baseline_param_val}'
        f'\nsolver progress: {solver.progress}'
        f'\nsolved_df: {solved_df}'
    )

    diff = abs(baseline_ba - solved_ba)
    assert diff <= solver.TOL, (
        f"Solver mismatch: |ΔBA|={diff:.4f} > {solver.TOL}."
    )
    # The baseline parameter value (before solving) should match the original
    # retirement milestone age (36).
    assert baseline_param_val == 36, (
        f"Expected baseline retirement age 36, got {baseline_param_val}"
    )

    # Sanity check that the solver actually changed the goal parameter value
    assert solved_val != baseline_param_val
