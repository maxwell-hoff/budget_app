from typing import List
from datetime import datetime

from ..models.milestone import Milestone
from ..models.goal import Goal
from ..models.scenario_parameter_value import ScenarioParameterValue
from ..models.solved_parameter_value import SolvedParameterValue
from ..database import db


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_for_goal(goal_parameter: str, milestones: List[Milestone]) -> None:
    """Compute solved values for **goal_parameter** for every supplied milestone.
    The algorithm walks through every ScenarioParameterValue attached to the milestone
    and constructs the full Cartesian product.  For a first pass we simplify to one
    parameter-at-a-time.
    """

    for ms in milestones:
        base_pv = _milestone_pv(ms)

        # Gather scenario parameter values grouped by parameter name
        param_to_values = {}
        for sv in ms.scenario_values:
            param_to_values.setdefault(sv.parameter, []).append(sv.value)

        # For now solve each scenario parameter independently (not Cartesian product).
        for scenario_parameter, values in param_to_values.items():
            for scenario_value in values:
                # Clone milestone with overridden parameter
                overridden = _clone_milestone(ms)
                setattr(overridden, scenario_parameter, _cast_value(scenario_value, overridden, scenario_parameter))

                # Naïve solve: keep all non-goal parameters fixed, so solved_value equals
                # the goal parameter value that makes PV match base.  We only support
                # linear solve for 'amount'.
                if goal_parameter == 'amount':
                    pv_ratio = base_pv / max(1e-9, _milestone_pv(overridden))
                    solved_val = overridden.amount * pv_ratio
                else:
                    # Placeholder: fall back to same value
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