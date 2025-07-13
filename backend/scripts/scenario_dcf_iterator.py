from collections import defaultdict
import math

from .db_connector import DBConnector
from .dcf_calculator_manual import DCFModel, Assumptions, GrowingSeries

# Reuse the Flask-SQLAlchemy session for writes so that data is visible everywhere
from backend.app.database import db  # type: ignore
from backend.app.models.dcf import DCF  # type: ignore


# ---------------------------------------------------------------------------
#  Helper functions to derive DCF inputs from milestones
# ---------------------------------------------------------------------------


def _norm_name(s: str | None) -> str:
    """Normalise milestone *name* for comparison.

    1. Convert to lower-case.
    2. Replace spaces and hyphens with an underscore so that
       "Current Salary" → "current_salary".
    """
    if s is None:
        return ""
    return s.strip().lower().replace(" ", "_").replace("-", "_")


# Map of milestone *name* → which DCF base input it controls ----------------
_CURRENT_MAP = {
    "current_salary": "income",
    "current_expenses": "expense",
    "current_liquid_assets": "asset",
    "current_liabilities": "liability",
}


def _is_current_ms(ms, start_age: int) -> bool:
    """Return ``True`` for milestones that happen **at the projection start**.

    A milestone is considered *current* when its ``age_at_occurrence`` equals
    the scenario's ``start_age``.  This captures opening balances and existing
    salary/expense levels without relying on the milestone name."""
    return ms.age_at_occurrence == start_age and ms.milestone_type in {"Asset", "Liability", "Income", "Expense"}


def _sum_amount(milestones, m_type, age):
    """Sum *amount* for milestones of *m_type* that occur at *age*."""
    return sum(
        m.amount or 0
        for m in milestones
        if (m.milestone_type == m_type and m.age_at_occurrence == age)
    )


# ---------------------------------------------------------------------------
#  ScenarioDCF – projection & persistence for a single scenario/sub-scenario
# ---------------------------------------------------------------------------


class ScenarioDCF:
    """Handle the end-to-end DCF projection for one Scenario → Sub-scenario pair."""

    def __init__(self, db_connector: DBConnector, scenario_id: int, sub_scenario_id: int):
        """Prepare a run for one (scenario_id, sub_scenario_id) pair."""

        # shared write-session
        self.session = db.session  # type: ignore

        # independent read-only session (avoids locking long transactions)
        self.read_session = db_connector.get_session()

        data = db_connector.fetch_all_data(self.read_session)
        self.milestones = [
            m for m in data["milestones"]
            if m.scenario_id == scenario_id and m.sub_scenario_id == sub_scenario_id
        ]

        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id

        if not self.milestones:
            raise ValueError(f"No milestones found for scenario {scenario_id}/{sub_scenario_id}")

        # — derive timeline bounds ------------------------------------------------
        self.start_age = min(m.age_at_occurrence for m in self.milestones)

        # When a milestone has a finite duration we need to project until the very
        # last year of that stream.  Otherwise we could truncate a salary that
        # ends at retirement, for example.
        end_candidates = [
            (m.age_at_occurrence + (m.duration or 0)) if (m.duration and m.duration > 0) else m.age_at_occurrence
            for m in self.milestones
        ]
        self.end_age = max(end_candidates)

        # ------------------------------------------------------------------
        # 1. Identify "current_*" milestones (single row each, occurring at
        #    start_age) that define the opening balances/flows.
        # ------------------------------------------------------------------
        current_vals = defaultdict(float)  # groups: asset/liability/income/expense

        for ms in self.milestones:
            if not _is_current_ms(ms, self.start_age):
                continue

            norm = _norm_name(ms.name)
            group_key = _CURRENT_MAP.get(norm)
            if group_key is None:
                # Fallback to milestone_type which maps 1:1 to the desired key
                group_key = ms.milestone_type.lower()
            current_vals[group_key] += ms.amount or 0.0

        self.initial_assets = current_vals.get("asset", None)
        self.initial_liabilities = current_vals.get("liability", None)
        self.base_salary = current_vals.get("income", None)
        self.base_expenses = current_vals.get("expense", None)

        # Legacy fallback – when the database does *not* yet store dedicated
        # current_* milestones we revert to the previous behaviour that summed
        # everything at *start_age*.
        if self.initial_assets is None:
            self.initial_assets = _sum_amount(self.milestones, "Asset", self.start_age)
        if self.initial_liabilities is None:
            self.initial_liabilities = _sum_amount(self.milestones, "Liability", self.start_age)
        if self.base_salary is None:
            self.base_salary = _sum_amount(self.milestones, "Income", self.start_age)
        if self.base_expenses is None:
            self.base_expenses = _sum_amount(self.milestones, "Expense", self.start_age)

        # ------------------------------------------------------------------
        # 2. Build cash-flow streams & one-off events from the remaining
        #    milestones.
        # ------------------------------------------------------------------
        self.income_streams: list[GrowingSeries] = []
        self.expense_streams: list[GrowingSeries] = []
        self.asset_events: list[tuple[int, float]] = []
        self.liability_events: list[tuple[int, float]] = []

        inflation_default = 0.03  # Same as used in run() call below

        legacy_assets_used = "asset" not in current_vals
        legacy_liabilities_used = "liability" not in current_vals

        for ms in self.milestones:
            # Skip the current_* milestones – already processed above
            if _is_current_ms(ms, self.start_age):
                continue

            mt = ms.milestone_type
            amt = ms.amount or 0.0

            # Convert monthly amounts to yearly so that the DCF (which works on
            # yearly periods) sees a like-for-like value.
            if (ms.occurrence or "Yearly") == "Monthly" and mt in ("Income", "Expense"):
                amt *= 12

            start_step = ms.age_at_occurrence - self.start_age
            duration = ms.duration if (ms.disbursement_type == "Fixed Duration") else None
            growth = ms.rate_of_return if ms.rate_of_return is not None else inflation_default

            if mt == "Income":
                self.income_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Expense":
                self.expense_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Asset":
                # Avoid double-counting: when we *did not* use current_liquid_assets
                # we already summed all assets at start_age into the opening balance.
                if legacy_assets_used and ms.age_at_occurrence == self.start_age:
                    # Already reflected in initial_assets
                    continue
                self.asset_events.append((ms.age_at_occurrence, amt))
            elif mt == "Liability":
                if legacy_liabilities_used and ms.age_at_occurrence == self.start_age:
                    continue

                # Keep principal as-is – do NOT multiply by 12
                liability_amt = amt

                # Convert duration & payment when the entry is specified monthly
                if (ms.occurrence or "Yearly") == "Monthly":
                    if ms.duration is not None:
                        ms.duration = max(int(math.ceil(ms.duration / 12)), 1)

                    if ms.payment is not None:
                        ms.payment = ms.payment * 12  # store annual figure so that downstream code can honour it

                self.liability_events.append((ms.age_at_occurrence, liability_amt))

        # ------------------------------------------------------------------
        # 3. Guarantee non-zero defaults so the DCF always runs.
        # ------------------------------------------------------------------
        self.initial_assets = self.initial_assets or 0.0
        self.initial_liabilities = self.initial_liabilities or 0.0
        self.base_salary = self.base_salary or 0.0
        self.base_expenses = self.base_expenses or 0.0

    # ---------------------------------------------------------------------
    #  DCF calculation & persistence
    # ---------------------------------------------------------------------

    def run(self):
        # Let DCFModel derive macro assumptions (inflation, ROI, cost_of_debt)
        # directly from milestones so that scenario-specific parameters are honoured.
        model = DCFModel.from_milestones(self.milestones).run()
        df = model.as_frame()

        # Map DataFrame → ORM rows (snake_case col names match DCF table)
        records = [
            DCF(
                scenario_id=self.scenario_id,
                sub_scenario_id=self.sub_scenario_id,
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

        self._upsert_rows(records)

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------

    def _upsert_rows(self, rows):
        """Insert or update the *rows* in the dcf table (idempotent)."""
        for r in rows:
            obj = (
                self.session.query(DCF)
                .filter_by(scenario_id=r.scenario_id, sub_scenario_id=r.sub_scenario_id, age=r.age)
                .one_or_none()
            )
            if obj is None:
                obj = r
            else:
                # Update all flow columns
                obj.beginning_assets = r.beginning_assets
                obj.assets_income = r.assets_income
                obj.beginning_liabilities = r.beginning_liabilities
                obj.liabilities_expense = r.liabilities_expense
                obj.salary = r.salary
                obj.expenses = r.expenses

            self.session.add(obj)

        self.session.commit()


# ---------------------------------------------------------------------------
#  ScenarioDCFIterator – loop over all combinations
# ---------------------------------------------------------------------------


class ScenarioDCFIterator:
    """Iterates over all Scenario → Sub-scenario combinations and calculates DCFs."""

    def __init__(self):
        self.db_connector = DBConnector()
        self.read_session = self.db_connector.get_session()

    def run(self):
        data = self.db_connector.fetch_all_data(self.read_session)
        combos = {
            (m.scenario_id, m.sub_scenario_id)
            for m in data["milestones"]
        }

        for scenario_id, sub_scenario_id in combos:
            try:
                sc_dcf = ScenarioDCF(self.db_connector, scenario_id, sub_scenario_id)
                sc_dcf.run()
            except ValueError:
                # Skip combinations without milestones – keeps behaviour identical
                continue


if __name__ == "__main__":
    ScenarioDCFIterator().run()
