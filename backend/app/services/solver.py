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


def _liquid_assets_for_milestones(rows: List[Milestone], current_age: int, target_age: int) -> float:
    """Return total liquid-asset balance at *target_age* for an *in-memory* list
    of Milestone objects (rows may or may not be persisted).  The computation
    mirrors NetWorthCalculator rules.  The list can safely include a clone of
    every milestone; function ignores any with name == 'Inheritance' because
    that row merely mirrors the total we are computing.
    """
    calc = NetWorthCalculator(current_age=current_age)
    total = 0.0
    for ms in rows:
        if ms.name == 'Inheritance':
            # The inheritance milestone amount equals liquid assets; exclude to
            # avoid circularity.
            continue
        val = calc.calculate_milestone_value_at_age(ms, target_age)
        if ms.milestone_type == 'Asset':
            total += val
        elif ms.milestone_type == 'Liability':
            # debt not part of liquid assets metric
            continue
        else:  # Income (+) or Expense (−) already signed
            total += val
    return total


def _search_goal_value(clone_ms: Milestone, all_rows: List[Milestone], goal_param: str,
                       baseline_target: float, inh_age: int) -> float:
    """Find the goal parameter value that makes liquid assets closest to the
    baseline_target.  Integer goals (age, duration) use exhaustive search; all
    others use a simple binary search and round to 1 decimal place."""

    def objective(candidate):
        setattr(clone_ms, goal_param, candidate)
        return abs(_liquid_assets_for_milestones(all_rows, 0, inh_age) - baseline_target)

    current_val = getattr(clone_ms, goal_param)

    if goal_param in {'age_at_occurrence', 'duration'}:
        best = current_val
        best_err = objective(best)
        for cand in range(0, inh_age + 1):
            err = objective(cand)
            if err < best_err:
                best, best_err = cand, err
        return best

    # decimal goal param search
    lo = 0.0
    hi = current_val * 10 if current_val else 1.0
    best = current_val
    best_err = objective(best)

    for _ in range(25):  # ~2^25 ≈ 3e7 resolution, plenty for 1-dp rounding
        mid = (lo + hi) / 2
        err_mid = objective(mid)
        if err_mid < best_err:
            best, best_err = mid, err_mid
        # decide search direction by seeing which side overshoots
        setattr(clone_ms, goal_param, mid)
        overshoot = _liquid_assets_for_milestones(all_rows, 0, inh_age) - baseline_target
        if overshoot > 0:
            hi = mid
        else:
            lo = mid
    return round(best, 1)


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

    baseline_cache = {}

    for ms in milestones:
        inh_age = _inheritance_age_for(ms)

        # Cache baseline liquid assets (excluding inheritance) for this scenario/sub-scenario
        scenario_key = (ms.scenario_id, ms.sub_scenario_id)
        if scenario_key not in baseline_cache:
            base_rows = Milestone.query.filter_by(
                scenario_id=ms.scenario_id,
                sub_scenario_id=ms.sub_scenario_id
            ).all()
            baseline_cache[scenario_key] = _liquid_assets_for_milestones(base_rows, 0, inh_age)

        baseline_target = baseline_cache[scenario_key]

        # Build a full clone list once per ms to reuse inside inner loop
        original_group_rows = Milestone.query.filter_by(
            scenario_id=ms.scenario_id,
            sub_scenario_id=ms.sub_scenario_id
        ).all()

        try:
            goal_index_in_group = next(i for i, r in enumerate(original_group_rows) if r.id == ms.id)
        except StopIteration:
            goal_index_in_group = None

        for scenario_parameter, values in global_param_values.items():
            for scenario_value in values:
                # fresh clone list for this variant
                clone_list = [_clone_milestone(r) for r in original_group_rows]

                if goal_index_in_group is None:
                    continue  # safety
                clone_ms = clone_list[goal_index_in_group]
                setattr(clone_ms, scenario_parameter, _cast_value(scenario_value, clone_ms, scenario_parameter))

                # search for goal value
                solved_val = _search_goal_value(
                    clone_ms, clone_list, goal_parameter,
                    baseline_target, inh_age
                )

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