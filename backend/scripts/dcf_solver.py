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
from backend.app.models.target_sub_scenario import TargetSubScenario


class DCFGoalSolver:
    """Find a goal-parameter value so that the ending Beginning-Assets balance
    matches the *base* projection value.

    The search uses a simple bisection algorithm and assumes the mapping
    goal_parameter → Ending BA is monotonous (see note in README).
    """

    MAX_ITER = 40
    TOL = 0.01  # absolute currency tolerance (≈ one cent)

    def __init__(self, milestones: List[Milestone], target_ba: float, anchor_age: int | None):
        # Work on *copies* so we never mutate DB-attached objects
        self.base_ms: List[Milestone] = copy.deepcopy(milestones)
        self.target_ba = target_ba
        self.anchor_age = anchor_age

        # Container tracking the solver path – useful for unit-tests / debugging.
        # Each element is a tuple ``(candidate_value, resulting_ba)``.
        self.progress: List[tuple[float, float]] = []

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

        # Record initial probes
        self.progress.append((low, ba_low))
        self.progress.append((high, ba_high))

        expand_iter = 0
        while not (min(ba_low, ba_high) <= self.target_ba <= max(ba_low, ba_high)) and expand_iter < 10:
            # Expand the interval exponentially until the target is bracketed
            span = (high - low) if high > low else (low - high)
            low -= span
            high += span
            ba_low = self._ba_for_value(working_ms, goal_ms, attr, low, is_age_attr)
            ba_high = self._ba_for_value(working_ms, goal_ms, attr, high, is_age_attr)

            # Track expansion probes
            self.progress.append((low, ba_low))
            self.progress.append((high, ba_high))
            expand_iter += 1

        # ------------------------------------------------------------------
        # Special handling for age parameters: if we still failed to bracket
        # the target after the limited expansion attempts, fall back to a
        # *discrete* search over the plausible human-age range.  Because the
        # model is evaluated yearly, being off by ±1 year is acceptable and
        # avoids runaway intervals that trigger floating-point overflow.
        # ------------------------------------------------------------------
        if is_age_attr and not (min(ba_low, ba_high) <= self.target_ba <= max(ba_low, ba_high)):
            best_age = None
            best_diff = float("inf")

            for age in range(0, 121):  # inclusive upper bound for clarity
                ba_val = self._ba_for_value(working_ms, goal_ms, attr, age, True)
                self.progress.append((age, ba_val))
                diff = abs(ba_val - self.target_ba)
                if diff < best_diff:
                    best_diff = diff
                    best_age = age

            solved_val = best_age if best_age is not None else initial_val
            setattr(goal_ms, attr, solved_val)
            return solved_val, working_ms

        # --- bisection -----------------------------------------------------
        for _ in range(self.MAX_ITER):
            mid = (low + high) / 2

            ba_mid = self._ba_for_value(working_ms, goal_ms, attr, mid, is_age_attr)

            # Log bisection probe -------------------------------------------------
            self.progress.append((mid, ba_mid))

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

        low = 0.0 if start >= 0 else start * 2
        high = start * 2 + 1 if start > 0 else 1.0
        if high <= low + 1e-9:
            high = low + 1.0
        return low, high

    def _ending_beginning_assets(self, milestones: List[Milestone]) -> float:
        df = DCFModel.from_milestones(milestones).run().as_frame()
        if self.anchor_age is not None:
            # Prefer BA at the specified anchor age when available
            try:
                row = df.loc[df.Age == self.anchor_age]
                if not row.empty:
                    return float(row["Beginning Assets"].iloc[0])
            except Exception:
                # Fall back to last age below
                pass
        return float(df.loc[df.Age == df.Age.max(), "Beginning Assets"].iloc[0])

    def _ba_for_value(self, milestones: List[Milestone], goal_ms: Milestone,
                      attr: str, val: float, is_age: bool) -> float:
        """Temporarily set *attr* on *goal_ms* to *val*, compute BA for *milestones*."""
        # Clamp age values to a sensible human range to avoid extreme horizon
        # lengths that can cause numerical overflow.
        if is_age:
            val = max(0, min(120, int(round(val))))

        original = getattr(goal_ms, attr)
        setattr(goal_ms, attr, val)
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

        # ------------------------------------------------------------------
        #  Determine the anchor Beginning Assets at the "inheritance age".
        #
        #  Anchor selection rules:
        #   - If the user marked a target sub-scenario for a scenario, use that
        #     sub-scenario's baseline DCF and pick the BA at the inheritance age
        #     of that target combo.
        #   - Otherwise, use the combo's own baseline DCF BA at its inheritance
        #     age (legacy behaviour – per combo, not global!).
        #
        #  Notes:
        #   - The baseline DCF projection (ScenarioDCFIterator) already clamps
        #     the projection horizon to inheritance age when one exists, so the
        #     BA at inheritance age usually equals the BA of the last row. We
        #     still explicitly look up by age when possible for clarity.
        # ------------------------------------------------------------------

        # Map scenario_id → sub_scenario_id of chosen target
        scenario_to_target_sub = {
            row.scenario_id: row.sub_scenario_id for row in self.read_session.query(TargetSubScenario).all()
        }

        # Build (scenario, sub) → [ {age → BA} ] from baseline DCF rows
        combo_ba_by_age: Dict[Tuple[int, int], Dict[int, float]] = {}
        combo_last_age: Dict[Tuple[int, int], int] = {}
        for row in base_dcf_rows:
            key = (row.scenario_id, row.sub_scenario_id)
            combo_ba_by_age.setdefault(key, {})[row.age] = row.beginning_assets
            # Track the last (max) age per combo as fallback
            if key not in combo_last_age or row.age > combo_last_age[key]:
                combo_last_age[key] = row.age

        # Map combo → milestones, goals, scenario params ----------------
        combo_ms: Dict[Tuple[int, int], List[Milestone]] = {}
        for m in milestones:
            combo_ms.setdefault((m.scenario_id, m.sub_scenario_id), []).append(m)

        # Compute inheritance age per combo (if present)
        combo_inh_age: Dict[Tuple[int, int], int] = {}
        for combo, ms_list in combo_ms.items():
            inh = next((m for m in ms_list if _norm_name(m.name) == "inheritance"), None)
            if inh is not None and isinstance(inh.age_at_occurrence, int):
                combo_inh_age[combo] = inh.age_at_occurrence

        goals: List[Goal] = data["goals"]
        spvs: List[ScenarioParameterValue] = data["scenario_parameter_values"]

        # Main loops ----------------------------------------------------
        solved_param_records: List[dict] = []
        solved_dcf_rows: List[SolvedDCF] = []

        # Cache per-scenario, per-parameter-value, per-milestone-group anchors
        # Key: (scenario_id, group_key, scenario_parameter, scenario_value) → (anchor_ba, anchor_age)
        scenario_spv_anchor_cache: Dict[Tuple[int, Tuple], Tuple[float, int]] = {}

        def _group_key(ms: Milestone) -> Tuple:
            """Return a cross-sub-scenario matching key for *ms*.

            Prefer parent_milestone_id when present; otherwise fall back to
            (name, milestone_type) which is stable across sub-scenarios.  We
            intentionally do not include age so that age-shifting parameters can
            still match their counterparts across sub-scenarios.
            """
            if getattr(ms, "parent_milestone_id", None):
                return ("parent", ms.parent_milestone_id)
            return ("name_type", (ms.name, ms.milestone_type))

        def _cast_any(v: str) -> Any:
            try:
                return float(v)
            except ValueError:
                return v

        for combo, ms_list in combo_ms.items():
            scenario_id, sub_scenario_id = combo

            # Decide anchor BA -----------------------------------------
            is_target_sub = scenario_to_target_sub.get(scenario_id) == sub_scenario_id

            def _lookup_anchor(for_combo: Tuple[int, int]) -> tuple[float | None, int | None]:
                # Try inheritance-age BA first
                inh_age = combo_inh_age.get(for_combo)
                ba_map = combo_ba_by_age.get(for_combo, {})
                if inh_age is not None and inh_age in ba_map:
                    return ba_map[inh_age], inh_age
                # Fallback to last available age for the combo
                last_age = combo_last_age.get(for_combo)
                if last_age is not None and last_age in ba_map:
                    return ba_map[last_age], last_age
                return None, None

            # We will compute the anchor per scenario-parameter value based on
            # the target sub-scenario when available.  Fallback: this combo's
            # own baseline at inheritance/last age.
            target_sub_id = scenario_to_target_sub.get(scenario_id)

            combo_goals = [g for g in goals if g.milestone_id in {m.id for m in ms_list} and g.is_goal]
            combo_spvs = [spv for spv in spvs if spv.milestone_id in {m.id for m in ms_list}]

            if not combo_goals or not combo_spvs:
                continue

            for spv in combo_spvs:
                # ---------------------------------------------------------
                # Target sub-scenario behaviour:
                # The target defines the benchmark for each scenario parameter
                # value; it is not re-solved.  We record the (possibly modified)
                # current goal parameter value after applying the spv locally.
                # ---------------------------------------------------------

                if is_target_sub:
                    # Apply this spv to the target combo's milestone clone and
                    # record the current goal parameter values as-is.
                    # Build lookup of milestones by id for quick access.
                    ms_by_id = {m.id: m for m in ms_list}
                    src_ms = ms_by_id.get(spv.milestone_id)
                    if src_ms is None:
                        continue
                    setattr(src_ms, spv.parameter, _cast_any(spv.value))

                    for goal in combo_goals:
                        goal_ms = ms_by_id.get(goal.milestone_id)
                        if goal_ms is None:
                            continue
                        baseline_goal_val = getattr(goal_ms, goal.parameter)
                        solved_param_records.append({
                            "milestone_id": goal.milestone_id,
                            "scenario_id": scenario_id,
                            "sub_scenario_id": sub_scenario_id,
                            "goal_parameter": goal.parameter,
                            "scenario_parameter": spv.parameter,
                            "scenario_value": spv.value,
                            "solved_value": baseline_goal_val,
                        })
                    continue

                # Compute per-spv anchor (shared across all sub-scenarios) ----
                if target_sub_id is not None:
                    # Anchor is based on the target combo with the same spv applied
                    target_combo = (scenario_id, target_sub_id)
                    target_ms_list = combo_ms.get(target_combo)
                    if target_ms_list is None:
                        continue

                    # Identify the matching milestone in the target to apply spv
                    src_ms = next((m for m in ms_list if m.id == spv.milestone_id), None)
                    if src_ms is None:
                        continue
                    gkey = _group_key(src_ms)
                    cache_key = (scenario_id, (gkey, spv.parameter, spv.value))

                    if cache_key not in scenario_spv_anchor_cache:
                        # Build a deep copy so we can mutate safely
                        target_copy = copy.deepcopy(target_ms_list)

                        # Find matching ms in target_copy
                        tgt_ms = None
                        for m in target_copy:
                            if _group_key(m) == gkey:
                                tgt_ms = m
                                break
                        if tgt_ms is None:
                            # Fallback: try matching by name only
                            for m in target_copy:
                                if m.name == src_ms.name and m.milestone_type == src_ms.milestone_type:
                                    tgt_ms = m
                                    break
                        if tgt_ms is None:
                            # As a last resort skip – cannot find anchor for this spv
                            continue

                        # Apply the spv on the target milestone
                        setattr(tgt_ms, spv.parameter, _cast_any(spv.value))

                        # Determine inheritance age for target combo
                        tgt_inh_ms = next((m for m in target_copy if _norm_name(m.name) == "inheritance"), None)
                        tgt_inh_age = tgt_inh_ms.age_at_occurrence if tgt_inh_ms else combo_last_age.get(target_combo, None)

                        # Run DCF and pick BA at anchor age
                        df_anchor = DCFModel.from_milestones(target_copy).run().as_frame()
                        anchor_ba_val: float
                        anchor_age_val: int
                        if tgt_inh_age is not None:
                            row = df_anchor.loc[df_anchor.Age == tgt_inh_age]
                            if not row.empty:
                                anchor_ba_val = float(row["Beginning Assets"].iloc[0])
                                anchor_age_val = int(tgt_inh_age)
                            else:
                                # fallback to last row
                                last_age_val = int(df_anchor.Age.max())
                                anchor_ba_val = float(df_anchor.loc[df_anchor.Age == last_age_val, "Beginning Assets"].iloc[0])
                                anchor_age_val = last_age_val
                        else:
                            last_age_val = int(df_anchor.Age.max())
                            anchor_ba_val = float(df_anchor.loc[df_anchor.Age == last_age_val, "Beginning Assets"].iloc[0])
                            anchor_age_val = last_age_val

                        scenario_spv_anchor_cache[cache_key] = (anchor_ba_val, anchor_age_val)

                    anchor_ba, anchor_age = scenario_spv_anchor_cache[cache_key]
                else:
                    # No target sub-scenario defined – use this combo's baseline
                    anchor_ba, anchor_age = _lookup_anchor(combo)
                    if anchor_ba is None:
                        continue

                for goal in combo_goals:
                    solver = DCFGoalSolver(ms_list, anchor_ba, anchor_age)
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
