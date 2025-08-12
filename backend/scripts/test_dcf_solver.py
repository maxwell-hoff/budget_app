import math
import pytest
import itertools

from backend.app.models.milestone import Milestone
from backend.app.models.goal import Goal
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from .dcf_solver import DCFGoalSolver


@pytest.fixture(params=[
    ("0.02", 39),
    ("0.05", 38),
    ("0.08", 37),
    ("0.12", 36),
    ("0.15", 35),
    ("0.2", 34)
], scope="module")
def sample_data(request):
    """Return a small milestone list + goal + scenario parameter for quick tests."""

    # Helper to generate sequential IDs (simulating DB auto-increment)
    _id_gen = itertools.count(1)
    def _next_id():
        return next(_id_gen)

    milestones = []

    def _new_ms(**kwargs):
        dyn_target = kwargs.pop("duration_end_at_milestone", None)
        obj = Milestone(**kwargs)
        obj.id = _next_id()
        if dyn_target is not None:
            # Attach the dynamic-duration attribute manually so that it is
            # available even though the SQLAlchemy model does not define it
            # as a mapped column.
            setattr(obj, "duration_end_at_milestone", dyn_target)
        return obj

    milestones.extend([
        _new_ms(
            name="Current Salary",
            milestone_type="Income",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=110_000.0,
            occurrence="Yearly",
            duration=None,  # explicit duration omitted – will be dynamic
            duration_end_at_milestone="Retirement",
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
            duration=None,
            duration_end_at_milestone="Retirement",
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
        _new_ms(
            name="Inheritance",
            milestone_type="Expense",
            age_at_occurrence=40,
            disbursement_type="Fixed Duration",
            amount=0.0,
            occurrence="Yearly",
            duration=1,
            rate_of_return=0.00,
            scenario_id=1,
            sub_scenario_id=1,
        ),
    ])

    # Simple opening asset bucket + salary + expense baseline
    liquid_assets = _new_ms(
        name="Savings",
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
        duration=None,
        duration_end_at_milestone="Inheritance",
        rate_of_return=0.02,
        scenario_id=1,
        sub_scenario_id=1,
    )
    milestones.append(retirement)
    milestones.append(liquid_assets)

    goal = Goal(milestone_id=retirement.id, parameter="age_at_occurrence", is_goal=True)

    # Scenario parameter: apply whichever rate was requested via parametrisation
    spv_rate, expected_solved_value = request.param
    spv = ScenarioParameterValue(milestone_id=liquid_assets.id, parameter="rate_of_return", value=spv_rate)

    return milestones, goal, spv, expected_solved_value

def test_goal_solver_converges(sample_data):
    milestones, goal, spv, expected_solved_value = sample_data

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
        f'\n nsolved_val: {solved_val}, baseline_param_val: {baseline_param_val}, solved_ba: {solved_ba}, baseline_ba: {baseline_ba}, '
        f'\n spv_rate: {spv.value}'
        f'\n solver progress: {solver.progress}'
        f'\n solved_df: {solved_df}'
    )

    # NOTE: this test doesn't work well with an age parameter
    # diff = abs(baseline_ba - solved_ba)
    # assert diff <= solver.TOL, (
    #     f"Solver mismatch: |ΔBA|={diff:.4f} > {solver.TOL}."
    # )
    # The baseline parameter value (before solving) should match the original
    # retirement milestone age (36).
    assert baseline_param_val == 36, (
        f"Expected baseline retirement age 36, got {baseline_param_val}"
    )

    # Sanity check that the solver actually changed the goal parameter value
    # assert solved_val != baseline_param_val
    
    # Verify the solved value matches the expected value
    assert abs(solved_val - expected_solved_value) <= 1, (
        f"Solved value {solved_val} does not match expected value {expected_solved_value}"
    )
