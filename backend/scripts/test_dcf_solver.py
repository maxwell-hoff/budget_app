import math
import pytest

from backend.app.models.milestone import Milestone
from backend.app.models.goal import Goal
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from .dcf_solver import DCFGoalSolver


@pytest.fixture(scope="module")
def sample_data():
    """Return a small milestone list + goal + scenario parameter for quick tests."""

    # Simple liquid asset + salary + expense baseline (like earlier unit-tests)
    milestones = [
        Milestone(
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
        Milestone(
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
        Milestone(
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
    ]

    # Simple liquid asset + salary + expense baseline (like earlier unit-tests)Milestone(
    liquid_assets = Milestone(
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
    retirement = Milestone(
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

    # Scenario parameter: shift rate of return to 6% instead of 8%
    spv = ScenarioParameterValue(milestone_id=liquid_assets.id, parameter="rate_of_return", value="0.105")

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
    # Fetch baseline value of the goal parameter before solving for clearer debug output
    baseline_param_val = next(m for m in milestones if m.id == goal.milestone_id).__dict__[goal.parameter]
    print(
        f'solved_ba: {solved_ba}, baseline_ba: {baseline_ba}, '
        f'solved_val: {solved_val}, baseline_param_val: {baseline_param_val}'
        f'solver progress: {solver.progress}'
    )

    diff = abs(baseline_ba - solved_ba)
    assert diff <= solver.TOL, (
        f"Solver mismatch: |ΔBA|={diff:.4f} > {solver.TOL}."
    )
    # Sanity check that value changed noticeably
    assert solved_val != goal.parameter
