from typing import List
from datetime import datetime

from ..models.milestone import Milestone
from ..models.goal import Goal
from ..models.scenario_parameter_value import ScenarioParameterValue
from ..models.solved_parameter_value import SolvedParameterValue
from ..database import db
from ..services.net_worth_calculator import NetWorthCalculator


def _present_value(amount: float, years: float, rate: float) -> float:
    """Very simple PV helper (continuous compounding not assumed)."""
    if rate is None:
        rate = 0.0
    return amount / ((1 + rate) ** years)


def _milestone_pv(ms: Milestone) -> float:
    """Calculate a crude present value for the milestone.  This is a stub; replace with
    the richer logic already used by the net-worth or liquidity calculations."""
    years = max(ms.age_at_occurrence - 0, 0)  # Assume 0 = present age baseline
    return _present_value(ms.amount, years, ms.rate_of_return or 0.0)


def _inheritance_age_for(ms: Milestone) -> int:
    """Return the age of the (first) Inheritance milestone in the same scenario / sub-scenario.
    Fallback to 100 if none exists."""
    inh = (
        Milestone.query.filter_by(
            name='Inheritance',
            scenario_id=ms.scenario_id,
            sub_scenario_id=ms.sub_scenario_id,
        ).first()
    )
    return inh.age_at_occurrence if inh else 100


def _milestone_value_at_age(ms: Milestone, target_age: int) -> float:
    """Proxy to NetWorthCalculator logic for a single milestone at *target_age*."""
    # We create a throw-away calculator; current_age does not matter for value calculation.
    calc = NetWorthCalculator(current_age=0)
    return calc.calculate_milestone_value_at_age(ms, target_age)


def _solve_age_for_value(match_value: float, proto_ms: Milestone, target_age: int, low: int, high: int, tol: float = 1.0) -> int:
    """Brute-force search for age in [low, high] whose value at *target_age* is ~ match_value.

    We evaluate every integer age in the range and return the one with smallest absolute
    difference to match_value.  tol provides an early-exit threshold."""
    best_age = proto_ms.age_at_occurrence
    best_diff = abs(_milestone_value_at_age(proto_ms, target_age) - match_value)

    for age in range(low, high + 1):
        proto_ms.age_at_occurrence = age
        val = _milestone_value_at_age(proto_ms, target_age)
        diff = abs(val - match_value)
        if diff < best_diff:
            best_age, best_diff = age, diff
            if best_diff <= tol:
                break
    # Restore (not strictly needed because object will be discarded)
    return best_age


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_for_goal(goal_parameter: str, milestones: List[Milestone]) -> None:
    """Compute solved values for **goal_parameter** for every supplied milestone.
    The algorithm walks through every ScenarioParameterValue attached to the milestone
    and constructs the full Cartesian product.  For a first pass we simplify to one
    parameter-at-a-time.
    """

    # Build global mapping of scenario parameter -> set(values) across *all* milestones
    global_param_values = {}
    for sv in ScenarioParameterValue.query.all():
        global_param_values.setdefault(sv.parameter, set()).add(sv.value)

    # Convert sets to sorted lists for deterministic iteration
    for k in global_param_values:
        global_param_values[k] = sorted(global_param_values[k], key=lambda x: (str(x)))

    for ms in milestones:
        base_pv = _milestone_pv(ms)
        # Pre-compute base value at inheritance age for potential age solving
        inh_age = _inheritance_age_for(ms)
        base_val_at_inh = _milestone_value_at_age(ms, inh_age)

        for scenario_parameter, values in global_param_values.items():
            for scenario_value in values:
                # Clone milestone with overridden parameter
                overridden = _clone_milestone(ms)
                setattr(overridden, scenario_parameter, _cast_value(scenario_value, overridden, scenario_parameter))

                if goal_parameter == 'amount':
                    # Keep PVs equal by scaling amount linearly.
                    pv_ratio = base_pv / max(1e-9, _milestone_pv(overridden))
                    solved_val = overridden.amount * pv_ratio

                elif goal_parameter == 'age_at_occurrence':
                    # Adjust age so that the milestone's contribution to liquid assets
                    # at inheritance age remains unchanged despite scenario variation.
                    low_bound = 0
                    high_bound = inh_age  # cannot occur after inheritance
                    solved_age = _solve_age_for_value(
                        match_value=base_val_at_inh,
                        proto_ms=overridden,
                        target_age=inh_age,
                        low=low_bound,
                        high=high_bound,
                    )
                    solved_val = solved_age

                else:
                    # Fallback: unchanged
                    solved_val = getattr(overridden, goal_parameter)

                _upsert_solved_value(ms, goal_parameter, scenario_parameter, scenario_value, solved_val)

    db.session.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clone_milestone(ms: Milestone) -> Milestone:
    """Return an *un-persisted* copy of the milestone row."""
    replica = Milestone(
        name=ms.name,
        age_at_occurrence=ms.age_at_occurrence,
        milestone_type=ms.milestone_type,
        disbursement_type=ms.disbursement_type,
        amount=ms.amount,
        payment=ms.payment,
        occurrence=ms.occurrence,
        duration=ms.duration,
        rate_of_return=ms.rate_of_return,
        order=ms.order,
        parent_milestone_id=ms.parent_milestone_id,
        scenario_id=ms.scenario_id,
        scenario_name=ms.scenario_name,
        sub_scenario_id=ms.sub_scenario_id,
        sub_scenario_name=ms.sub_scenario_name,
    )
    return replica


def _cast_value(val: str, ms: Milestone, param: str):
    """Cast scenario value string to the attribute's type (best-effort)."""
    current = getattr(ms, param, None)
    if isinstance(current, (int, float)):
        try:
            return float(val)
        except ValueError:
            return current
    return val


def _upsert_solved_value(ms: Milestone, goal_param: str, scenario_param: str, scenario_val: str, solved_val: float):
    """Insert or update a solved value row."""
    row = SolvedParameterValue.query.filter_by(
        milestone_id=ms.id,
        goal_parameter=goal_param,
        scenario_parameter=scenario_param,
        scenario_value=str(scenario_val)
    ).first()

    if row is None:
        row = SolvedParameterValue(
            milestone_id=ms.id,
            scenario_id=ms.scenario_id,
            sub_scenario_id=ms.sub_scenario_id,
            goal_parameter=goal_param,
            scenario_parameter=scenario_param,
            scenario_value=str(scenario_val),
            solved_value=solved_val,
        )
        db.session.add(row)
    else:
        row.solved_value = solved_val
        row.updated_at = datetime.utcnow() 