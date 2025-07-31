"""Monte Carlo simulation runner for discounted-cash-flow (DCF) projections.

This script iterates through every (scenario, sub-scenario, scenario-parameter)
combination in the database, draws *N* random samples from a configurable
probability distribution (Normal by default) around the baseline parameter
value and evaluates the resulting DCF path.

For every combination we *only* persist the simulation path that produced the
highest and the lowest **ending beginning-assets** balance at age 100 (or the
last simulated age when the projection ends before 100).

The projection data is stored in the new ``monte_carlo_dcf`` table which mirrors
``solved_dcf`` with an additional ``result_type`` column ("max" or "min").

The module also exposes :func:`simulate_milestones` for unit-tests and ad-hoc
analysis without touching the database.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
#  Ensure the project root is on PYTHONPATH so that `import backend.*` works
#  when the script is executed as a *file* (e.g. `python backend/scripts/...`).
# ---------------------------------------------------------------------------
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import argparse
import copy
import math
from typing import List, Tuple

import numpy as np

from backend.app.database import db  # Flask-SQLAlchemy instance – needed for writes
from backend.app.models.monte_carlo_dcf import MonteCarloDCF
from backend.app.models.scenario_parameter_value import ScenarioParameterValue
from backend.scripts.db_connector import DBConnector
from backend.scripts.dcf_calculator_manual import DCFModel
from backend.app.models.milestone import Milestone

# ---------------------------------------------------------------------------
#  Helpers – apply scenario parameter value to a milestone list
# ---------------------------------------------------------------------------

def _apply_param(milestones: List[Milestone], spv: ScenarioParameterValue) -> None:
    """In-place update of *milestones* (deep-copy recommended by caller!)."""
    ms = next(m for m in milestones if m.id == spv.milestone_id)

    # ScenarioParameterValue.value is *always* stored as *str* in the DB so we
    # attempt a best-effort numeric cast first, falling back to string.
    try:
        val = float(spv.value)
    except ValueError:
        val = spv.value

    setattr(ms, spv.parameter, val)

# ---------------------------------------------------------------------------
#  Core Monte Carlo routine – reusable, side-effect free
# ---------------------------------------------------------------------------

def _ending_ba(df) -> float:
    """Return Beginning-Assets of the last row *or* age 100 when available."""
    if (df.Age == 100).any():
        return float(df.loc[df.Age == 100, "Beginning Assets"].iloc[0])
    return float(df["Beginning Assets"].iloc[-1])


def simulate_milestones(
    base_milestones: List[Milestone],
    spv: ScenarioParameterValue,
    *,
    iterations: int = 1000,
    sigma: float | None = None,
    debug: bool = False,
) -> Tuple[Tuple[int, object], Tuple[int, object]]:
    """Run Monte Carlo over *base_milestones* varying *spv*.

    Parameters
    ----------
    base_milestones: List[Milestone]
        Milestones that make up the scenario (will **not** be mutated).
    spv: ScenarioParameterValue
        The scenario parameter that will be sampled from a distribution.
    iterations: int, default 1000
        Number of random draws.
    sigma: float | None, default None
        Standard deviation **relative** to *mu* when given as a fraction (e.g. 0.1
        → 10 %).  When *None* the fallback is *0.1 × |mu|* for numeric parameters
        and raises *ValueError* for non-numeric parameters.
    debug: bool, default False
        Print every sampled value + resulting ending BA – useful to trace single
        simulations.

    Returns
    -------
    (best_iter, best_df), (worst_iter, worst_df)
        • *best_df* produces the highest ending BA.
        • *worst_df* produces the lowest ending BA.
    """

    # Guard against accidental mutation of caller-provided milestone list
    base_ms = copy.deepcopy(base_milestones)

    # Baseline value (mu) -------------------------------------------------
    try:
        mu = float(spv.value)
        is_numeric = True
    except ValueError:
        mu = spv.value  # keep as string
        is_numeric = False

    if not is_numeric:
        raise ValueError("Monte Carlo only supports numeric scenario parameters for now.")

    # Choose σ ------------------------------------------------------------
    if sigma is None:
        sigma = 0.1 * abs(mu) if mu != 0 else 0.01  # fallback for zero baseline

    best_df = None
    best_ba = -math.inf
    best_iter = -1

    worst_df = None
    worst_ba = math.inf
    worst_iter = -1

    rng = np.random.default_rng()

    for i in range(iterations):
        candidate_ms = copy.deepcopy(base_ms)

        # Random draw ----------------------------------------------------
        sample_val = rng.normal(loc=mu, scale=sigma)

        # Clamp ages to human range when parameter is "age_at_occurrence" -----
        if spv.parameter == "age_at_occurrence":
            sample_val = max(0, min(120, int(round(sample_val))))

        # Apply sampled parameter ----------------------------------------
        spv_sample = copy.deepcopy(spv)
        spv_sample.value = str(sample_val)
        _apply_param(candidate_ms, spv_sample)

        # Run DCF ---------------------------------------------------------
        df = DCFModel.from_milestones(candidate_ms).run().as_frame()
        ending_ba = _ending_ba(df)

        if debug:
            print(f"iter {i:04d}: sample={sample_val}  ending_BA={ending_ba}")

        if ending_ba > best_ba:
            best_ba, best_df, best_iter = ending_ba, df, i
        if ending_ba < worst_ba:
            worst_ba, worst_df, worst_iter = ending_ba, df, i

    # mypy appeasement – both must be set because at least 1 iteration
    assert best_df is not None and worst_df is not None  # noqa

    return (best_iter, best_df), (worst_iter, worst_df)

# ---------------------------------------------------------------------------
#  Runner that persists results in the DB
# ---------------------------------------------------------------------------

class MonteCarloSimulator:
    """High-level orchestrator that works directly on the DB."""

    def __init__(self, *, iterations: int = 1000, sigma: float | None = None, debug: bool = False):
        self.iterations = iterations
        self.sigma = sigma
        self.debug = debug

        self.db_connector = DBConnector()
        self.read_session = self.db_connector.get_session()
        self.write_session = db.session  # reuse Flask-SQLAlchemy session so that other parts see the data

    # ------------------------------------------------------------------
    def run(self):
        data = self.db_connector.fetch_all_data(self.read_session)
        milestones: List[Milestone] = data["milestones"]
        spvs: List[ScenarioParameterValue] = data["scenario_parameter_values"]

        # Group milestones by their (scenario_id, sub_scenario_id) so lookups are O(1)
        ms_by_combo: dict[tuple[int, int], list[Milestone]] = {}
        ms_by_id: dict[int, Milestone] = {}
        for m in milestones:
            ms_by_combo.setdefault((m.scenario_id, m.sub_scenario_id), []).append(m)
            ms_by_id[m.id] = m

        for spv in spvs:
            ms = ms_by_id.get(spv.milestone_id)
            if ms is None:
                # dangling reference – skip
                continue
            combo = (ms.scenario_id, ms.sub_scenario_id)
            base_ms = ms_by_combo[combo]

            try:
                (best_iter, best_df), (worst_iter, worst_df) = simulate_milestones(
                    base_ms,
                    spv,
                    iterations=self.iterations,
                    sigma=self.sigma,
                    debug=self.debug,
                )
            except ValueError:
                # Non-numeric parameter – log & skip without aborting the batch
                if self.debug:
                    print(f"Skipping non-numeric parameter {spv.parameter}={spv.value}")
                continue

            # Persist the best & worst paths --------------------------------
            self._upsert_df(best_df, spv, result_type="max", iteration=best_iter)
            self._upsert_df(worst_df, spv, result_type="min", iteration=worst_iter)

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------
    def _upsert_df(self, df, spv: ScenarioParameterValue, *, result_type: str, iteration: int):
        rows = [
            MonteCarloDCF(
                scenario_id=self._scenario_id_for_spv(spv),
                sub_scenario_id=self._sub_scenario_id_for_spv(spv),
                scenario_parameter=spv.parameter,
                scenario_value=spv.value,
                result_type=result_type,
                iteration=iteration,
                age=int(row.Age),
                beginning_assets=row["Beginning Assets"],
                assets_income=row["Assets Income"],
                beginning_liabilities=row["Beginning Liabilities"],
                liabilities_expense=row["Liabilities Expense"],
                salary=row["Salary"],
                expenses=row["Expenses"],
            )
            for _, row in df.iterrows()
        ]

        for r in rows:
            obj = (
                self.write_session.query(MonteCarloDCF)
                .filter_by(
                    scenario_id=r.scenario_id,
                    sub_scenario_id=r.sub_scenario_id,
                    scenario_parameter=r.scenario_parameter,
                    scenario_value=r.scenario_value,
                    result_type=r.result_type,
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
                obj.iteration = r.iteration
            self.write_session.add(obj)

        self.write_session.commit()

    # ------------------------------------------------------------------
    def _milestone_for_spv(self, spv: ScenarioParameterValue) -> Milestone:
        return self.read_session.query(Milestone).filter_by(id=spv.milestone_id).one()

    def _scenario_id_for_spv(self, spv: ScenarioParameterValue) -> int:
        return self._milestone_for_spv(spv).scenario_id

    def _sub_scenario_id_for_spv(self, spv: ScenarioParameterValue) -> int:
        return self._milestone_for_spv(spv).sub_scenario_id

# ---------------------------------------------------------------------------
#  CLI entry-point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monte-Carlo DCF simulation runner")
    p.add_argument("--iterations", type=int, default=1000, help="Number of Monte Carlo iterations per parameter (default 1000)")
    p.add_argument(
        "--sigma",
        type=float,
        default=None,
        help="Standard deviation of the normal distribution relative to the mean when given as a fraction (e.g. 0.1 → 10 %). \n"
             "When omitted, defaults to 10 % of the baseline value.",
    )
    p.add_argument("--debug", action="store_true", help="Print every iteration with sampled value + ending BA")
    return p.parse_args()


def main():
    args = _parse_args()
    sim = MonteCarloSimulator(iterations=args.iterations, sigma=args.sigma, debug=args.debug)
    sim.run()


if __name__ == "__main__":
    main()

