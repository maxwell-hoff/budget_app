from __future__ import annotations

import copy
from typing import List, Dict, Tuple, Iterable, Any

from .db_connector import DBConnector
from .dcf_calculator_manual import DCFModel
from .scenario_dcf_iterator import _norm_name  # reuse helper
from backend.app.models.milestone import Milestone
from backend.app.models.goal import Goal
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from backend.app.models.solved_parameter_value import SolvedParameterValue
from backend.app.models.solved_dcf import SolvedDCF  # newly added
from backend.app.models.dcf import DCF
from backend.app.database import db  # Flask-SQLAlchemy instance


class DCFGoalSolver:
    """Find a goal-parameter value so that the ending Beginning-Assets balance
    matches the *base* projection value.

    The search uses a simple bisection algorithm and assumes the mapping
    goal_parameter → Ending BA is monotonous (see note in README).
    """

    MAX_ITER = 40
    TOL = 0.01  # absolute currency tolerance (≈ one cent)

    def __init__(self, milestones: List[Milestone], target_ba: float):
        # Work on *copies* so we never mutate DB-attached objects
        self.base_ms: List[Milestone] = copy.deepcopy(milestones)
        self.target_ba = target_ba

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    def solve(self, goal: Goal, scenario_param: ScenarioParameterValue) -> Tuple[float, List[Milestone]]:
        """Return (solved_goal_value, solved_milestones_copy)."""

        # --- build milestone list with the scenario parameter value applied
        working_ms: List[Milestone] = copy.deepcopy(self.base_ms)
        self._apply_param(working_ms, scenario_param)

        # Identify the milestone & attribute we have to tweak for the goal
        goal_ms = next(m for m in working_ms if m.id == goal.milestone_id)
        attr = goal.parameter

        # Pick initial bounds ------------------------------------------------
        initial_val = getattr(goal_ms, attr) or 0.0
        low, high = self._initial_bounds(initial_val)

        solved_val = initial_val
        is_age_attr = attr == "age_at_occurrence"

        # --- ensure the target BA lies between the BA at the bounds -------
        ba_low = self._ba_for_value(working_ms, goal_ms, attr, low, is_age_attr)
        ba_high = self._ba_for_value(working_ms, goal_ms, attr, high, is_age_attr)

        expand_iter = 0
        while not (min(ba_low, ba_high) <= self.target_ba <= max(ba_low, ba_high)) and expand_iter < 10:
            # Expand the interval exponentially until the target is bracketed
            span = (high - low) if high > low else (low - high)
            low -= span
            high += span
            ba_low = self._ba_for_value(working_ms, goal_ms, attr, low, is_age_attr)
            ba_high = self._ba_for_value(working_ms, goal_ms, attr, high, is_age_attr)
            expand_iter += 1

        # --- bisection -----------------------------------------------------
        for _ in range(self.MAX_ITER):
            mid = (low + high) / 2

            ba_mid = self._ba_for_value(working_ms, goal_ms, attr, mid, is_age_attr)

            if abs(ba_mid - self.target_ba) <= self.TOL:
                solved_val = int(round(mid)) if is_age_attr else mid
                break

            # Maintain the bracket
            if (ba_low - self.target_ba) * (ba_mid - self.target_ba) < 0:
                high = mid
                ba_high = ba_mid
            else:
                low = mid
                ba_low = ba_mid

            solved_val = int(round(mid)) if is_age_attr else mid

        # Ensure final milestone list has the converged value
        setattr(goal_ms, attr, solved_val)
        return solved_val, working_ms

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    def _apply_param(self, milestones: List[Milestone], spv: ScenarioParameterValue) -> None:
        """Mutate *milestones* in-place, applying the scenario param value."""
        ms = next(m for m in milestones if m.id == spv.milestone_id)
        val: Any = self._cast_value(spv.value)
        setattr(ms, spv.parameter, val)

    def _cast_value(self, v: str):
        try:
            return float(v)
        except ValueError:
            return v  # non-numeric – leave as string

    def _initial_bounds(self, start: float) -> Tuple[float, float]:
        """Return (low, high) suitable for bisection.

        If solving an *age* parameter we bound by [0, 120].
        Otherwise we use a simple 0↔double rule.
        """
        if isinstance(start, (int, float)) and abs(start) < 1e5 and start >= 0:
            # Heuristic: treat values in human-age range as age_at_occurrence
            low, high = 0, 120
            return float(low), float(high)

        low = 0.0 if start >= 0 else start * 3
        high = start * 3 + 1 if start > 0 else 1.0
        if high <= low + 1e-9:
            high = low + 1.0
        return low, high

    def _ending_beginning_assets(self, milestones: List[Milestone]) -> float:
        df = DCFModel.from_milestones(milestones).run().as_frame()
        return float(df.loc[df.Age == df.Age.max(), "Beginning Assets"].iloc[0])

    def _ba_for_value(self, milestones: List[Milestone], goal_ms: Milestone,
                      attr: str, val: float, is_age: bool) -> float:
        """Temporarily set *attr* on *goal_ms* to *val*, compute BA for *milestones*."""
        original = getattr(goal_ms, attr)
        setattr(goal_ms, attr, int(round(val)) if is_age else val)
        ba = self._ending_beginning_assets(milestones)
        setattr(goal_ms, attr, original)
        return ba


# ---------------------------------------------------------------------------
#  High-level orchestrator – iterates through DB rows
# ---------------------------------------------------------------------------
class DCFSolverRunner:

    def __init__(self):
        self.db_connector = DBConnector()
        self.read_session = self.db_connector.get_session()
        self.write_session = db.session  # use Flask-SQLAlchemy session for upserts

    # ------------------------------------------------------------------
    def run(self):
        data = self.db_connector.fetch_all_data(self.read_session)
        milestones: List[Milestone] = data["milestones"]
        base_dcf_rows: List[DCF] = self.read_session.query(DCF).all()

        # Group helpers ------------------------------------------------
        combo_to_target_ba: Dict[Tuple[int, int], float] = {}
        for row in base_dcf_rows:
            key = (row.scenario_id, row.sub_scenario_id)
            if key not in combo_to_target_ba or row.age > combo_to_target_ba[key][0]:
                combo_to_target_ba[key] = row.beginning_assets

        # Map combo → milestones, goals, scenario params ----------------
        combo_ms: Dict[Tuple[int, int], List[Milestone]] = {}
        for m in milestones:
            combo_ms.setdefault((m.scenario_id, m.sub_scenario_id), []).append(m)

        goals: List[Goal] = data["goals"]
        spvs: List[ScenarioParameterValue] = data["scenario_parameter_values"]

        # Main loops ----------------------------------------------------
        solved_param_records: List[dict] = []
        solved_dcf_rows: List[SolvedDCF] = []

        for combo, ms_list in combo_ms.items():
            scenario_id, sub_scenario_id = combo
            target_ba = combo_to_target_ba.get(combo)
            if target_ba is None:
                continue  # baseline missing – skip

            combo_goals = [g for g in goals if g.milestone_id in {m.id for m in ms_list} and g.is_goal]
            combo_spvs = [spv for spv in spvs if spv.milestone_id in {m.id for m in ms_list}]

            if not combo_goals or not combo_spvs:
                continue

            for spv in combo_spvs:
                for goal in combo_goals:
                    solver = DCFGoalSolver(ms_list, target_ba)
                    solved_val, solved_ms = solver.solve(goal, spv)

                    # Persist solved_param_value ----------------------
                    solved_param_records.append({
                        "milestone_id": goal.milestone_id,
                        "scenario_id": scenario_id,
                        "sub_scenario_id": sub_scenario_id,
                        "goal_parameter": goal.parameter,
                        "scenario_parameter": spv.parameter,
                        "scenario_value": spv.value,
                        "solved_value": solved_val,
                    })

                    # Build and store solved DCF rows -----------------
                    df = DCFModel.from_milestones(solved_ms).run().as_frame()
                    for _, row in df.iterrows():
                        solved_dcf_rows.append(
                            SolvedDCF(
                                scenario_id=scenario_id,
                                sub_scenario_id=sub_scenario_id,
                                goal_parameter=goal.parameter,
                                scenario_parameter=spv.parameter,
                                scenario_value=spv.value,
                                age=int(row.Age),
                                beginning_assets=row["Beginning Assets"],
                                assets_income=row["Assets Income"],
                                beginning_liabilities=row["Beginning Liabilities"],
                                liabilities_expense=row["Liabilities Expense"],
                                salary=row["Salary"],
                                expenses=row["Expenses"],
                            )
                        )

        # ---- commit all rows ------------------------------------------
        self._upsert_solved_dcf(solved_dcf_rows)
        self.db_connector.upsert_solved_parameter_values(self.write_session, solved_param_records)

    # ------------------------------------------------------------------
    def _upsert_solved_dcf(self, rows: Iterable[SolvedDCF]):
        for r in rows:
            obj = (
                self.write_session.query(SolvedDCF)
                .filter_by(
                    scenario_id=r.scenario_id,
                    sub_scenario_id=r.sub_scenario_id,
                    goal_parameter=r.goal_parameter,
                    scenario_parameter=r.scenario_parameter,
                    scenario_value=r.scenario_value,
                    age=r.age,
                )
                .one_or_none()
            )
            if obj is None:
                obj = r
            else:
                obj.beginning_assets = r.beginning_assets
                obj.assets_income = r.assets_income
                obj.beginning_liabilities = r.beginning_liabilities
                obj.liabilities_expense = r.liabilities_expense
                obj.salary = r.salary
                obj.expenses = r.expenses
            self.write_session.add(obj)
        self.write_session.commit()


if __name__ == "__main__":
    DCFSolverRunner().run()
