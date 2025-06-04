# dcf_model.py
# --------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd


# ────────────────────────────────────────────────────────────────────
#  Core assumptions
# ────────────────────────────────────────────────────────────────────
@dataclass
class Assumptions:
    """
    Non-optional macro levers for the entire model.

    Parameters
    ----------
    inflation       : annual CPI inflation (decimal, e.g. 0.03 = 3 %)
    rate_of_return  : yearly growth on invested assets (decimal)
    cost_of_debt    : yearly interest paid on liabilities (decimal)
    """
    inflation: float
    rate_of_return: float
    cost_of_debt: float


# ────────────────────────────────────────────────────────────────────
#  Helper cash-flow stream
# ────────────────────────────────────────────────────────────────────
@dataclass
class GrowingSeries:
    """A geometric series—e.g., salary growing with inflation.

    Parameters
    ----------
    initial_value : float
        Cash-flow amount at *start_step* (per period, i.e. per year in our model).
    growth_rate : float
        Geometric growth applied *yearly* (e.g. inflation).
    start_step : int, default 0
        Offset (in model steps/years) **relative to the model's ``start_age``** at
        which the cash-flow starts.  A value of ``5`` means the flow begins five
        years after the projection start.
    duration : int | None, default None
        Number of periods the cash-flow lasts.  ``None`` means it continues
        indefinitely (i.e. until ``end_age``).
    """

    initial_value: float
    growth_rate: float
    start_step: int = 0
    duration: int | None = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def value_at(self, step: int) -> float:
        """Return the cash-flow at *step* (0-based from model start).

        The series is **inactive** outside the half-open interval
        ``[start_step, start_step + duration)``.  When *duration* is ``None`` the
        interval extends to infinity.
        """

        if step < self.start_step:
            return 0.0

        rel_step = step - self.start_step

        if self.duration is not None and rel_step >= self.duration:
            return 0.0

        return self.initial_value * (1 + self.growth_rate) ** rel_step


# ────────────────────────────────────────────────────────────────────
#  Main DCF engine
# ────────────────────────────────────────────────────────────────────
class DCFModel:
    """
    Finite-horizon, yearly projection that mirrors 'Budget Test.xlsx'.

    Required parameters (everything must be supplied explicitly!):
        start_age, end_age,
        assumptions (Assumptions),
        initial_assets, initial_liabilities,
        base_salary, base_expenses
    """

    def __init__(
        self,
        *,
        start_age: int,
        end_age: int,
        assumptions: Assumptions,
        initial_assets: float,
        initial_liabilities: float,
        base_salary: float = 0.0,
        base_expenses: float = 0.0,
        income_streams: List[GrowingSeries] | None = None,
        expense_streams: List[GrowingSeries] | None = None,
        asset_events: List[tuple[int, float]] | None = None,
        liability_events: List[tuple[int, float]] | None = None,
    ):
        # ── store scenario settings ────────────────────────────────
        self.start_age = start_age
        self.end_age = end_age
        self.assump = assumptions

        # ── cash-flow drivers ─────────────────────────────────────
        self.income_streams: List[GrowingSeries] = [] if income_streams is None else list(income_streams)
        self.expense_streams: List[GrowingSeries] = [] if expense_streams is None else list(expense_streams)

        # Maintain backward compatibility with the old API ------------------
        if base_salary:
            self.income_streams.append(GrowingSeries(base_salary, self.assump.inflation))
        if base_expenses:
            self.expense_streams.append(GrowingSeries(base_expenses, self.assump.inflation))

        # ── state variables over time ──────────────────────────────
        self.assets: List[float] = [initial_assets]
        self.liabilities: List[float] = [initial_liabilities]

        # one-off balance adjustments (e.g. inheritance at age 40) ----------
        self._asset_events = {age: amt for age, amt in (asset_events or [])}
        self._liability_events = {age: amt for age, amt in (liability_events or [])}

        # results populated by run()
        self._table: pd.DataFrame | None = None

    # ─────────────────────── public API ─────────────────────────────
    def run(self) -> "DCFModel":
        """Iterates year by year and fills the internal DataFrame."""
        years = self.end_age - self.start_age
        rows: List[Dict] = []

        for t in range(years + 1):
            age = self.start_age + t

            # Apply one-off balance events at *beginning* of the year ---------
            a_begin_prev = self.assets[-1]
            l_begin_prev = self.liabilities[-1]
            a_begin = a_begin_prev + self._asset_events.get(age, 0.0)
            l_begin = l_begin_prev + self._liability_events.get(age, 0.0)

            # yearly flows ----------------------------------------------------
            salary = sum(s.value_at(t) for s in self.income_streams)
            expenses = sum(s.value_at(t) for s in self.expense_streams)
            a_income = a_begin * self.assump.rate_of_return
            l_interest = l_begin * self.assump.cost_of_debt  # also equals principal repayment

            net_saving = salary - expenses - l_interest
            a_next = a_begin + a_income + net_saving
            l_next = l_begin - l_interest

            if t < years:
                self.assets.append(a_next)
                self.liabilities.append(l_next)

            rows.append({
                "Age": age,
                "Beginning Assets": round(a_begin, 10),
                "Assets Income": round(a_income, 10),
                "Beginning Liabilities": round(l_begin, 10),
                "Liabilities Expense": round(l_interest, 10),
                "Salary": round(salary, 10),
                "Expenses": round(expenses, 10),
            })

        self._table = pd.DataFrame(rows)
        return self

    def as_frame(self) -> pd.DataFrame:
        if self._table is None:
            raise RuntimeError("run() must be called before retrieving results.")
        return self._table

    def summary(self) -> Dict[str, float]:
        if self._table is None:
            raise RuntimeError("run() must be called before retrieving results.")
        return {
            "Ending assets balance": float(self.assets[-1]),
            "Ending liabilities": float(self.liabilities[-1]),
            "Net worth": float(self.assets[-1] - self.liabilities[-1]),
        }

    # ── extension hooks (empty for now, ready for overrides) ───────
    def add_income_stream(self, stream: GrowingSeries) -> None:
        self.income_streams.append(stream)

    def add_expense_stream(self, stream: GrowingSeries) -> None:
        self.expense_streams.append(stream)

    # ------------------------------------------------------------------
    #  Convenience constructor – build a DCFModel directly from milestones
    # ------------------------------------------------------------------

    @classmethod
    def from_milestones(
        cls,
        milestones: List[object],
        *,
        assumptions: Assumptions | None = None,
        inflation_default: float = 0.03,
    ) -> "DCFModel":
        """Create a DCFModel from a list of milestone *records*.

        The *records* may either be the real ORM objects (having attributes like
        ``name``, ``milestone_type`` …) **or** plain dictionaries with the same
        keys.  This mirrors the database schema so that unit tests can easily
        supply mocked-up data without touching SQLAlchemy.
        """

        # ------------------------------------------------------------------
        # 1. Helper closures – kept local to avoid polluting the class API
        # ------------------------------------------------------------------

        def _get(attr: str, obj):
            """Return *attr* from *obj* whether it is an object or a dict."""
            if isinstance(obj, dict):
                return obj.get(attr)
            return getattr(obj, attr)

        def _norm_name(s: str | None) -> str:
            if s is None:
                return ""
            return s.strip().lower().replace(" ", "_").replace("-", "_")

        _CURRENT_MAP = {
            "current_salary": "income",
            "current_expenses": "expense",
            "current_liquid_assets": "asset",
            "current_liabilities": "liability",
        }

        def _is_current(ms) -> bool:
            return _norm_name(_get("name", ms)) in _CURRENT_MAP

        # ------------------------------------------------------------------
        # 2. Derive projection horizon
        # ------------------------------------------------------------------

        ages = [_get("age_at_occurrence", m) for m in milestones]
        if not ages:
            raise ValueError("No milestones supplied – cannot build DCF model.")

        start_age = min(ages)

        end_candidates = [
            (_get("age_at_occurrence", m) + ((_get("duration", m) or 0) - 1))
            if (_get("duration", m) and _get("duration", m) > 0)
            else _get("age_at_occurrence", m)
            for m in milestones
        ]
        end_age = max(end_candidates)

        # ------------------------------------------------------------------
        # 3. Opening balances & base flows from "current_*" milestones
        # ------------------------------------------------------------------

        current_vals: Dict[str, float] = {"asset": 0.0, "liability": 0.0, "income": 0.0, "expense": 0.0}

        for ms in milestones:
            if not _is_current(ms):
                continue
            key = _CURRENT_MAP[_norm_name(_get("name", ms))]
            current_vals[key] += _get("amount", ms) or 0.0

        # Fallback to legacy behaviour if explicit current_* milestones are absent
        def _sum_amount(m_type, age):
            return sum(
                (_get("amount", x) or 0.0)
                for x in milestones
                if (_get("milestone_type", x) == m_type and _get("age_at_occurrence", x) == age)
            )

        if current_vals["asset"] == 0.0:
            current_vals["asset"] = _sum_amount("Asset", start_age)
        if current_vals["liability"] == 0.0:
            current_vals["liability"] = _sum_amount("Liability", start_age)
        if current_vals["income"] == 0.0:
            current_vals["income"] = _sum_amount("Income", start_age)
        if current_vals["expense"] == 0.0:
            current_vals["expense"] = _sum_amount("Expense", start_age)

        # ------------------------------------------------------------------
        # 4. Convert remaining milestones → streams / events
        # ------------------------------------------------------------------

        income_streams: List[GrowingSeries] = []
        expense_streams: List[GrowingSeries] = []
        asset_events: List[tuple[int, float]] = []
        liability_events: List[tuple[int, float]] = []

        legacy_assets_used = current_vals["asset"] == _sum_amount("Asset", start_age)
        legacy_liabs_used = current_vals["liability"] == _sum_amount("Liability", start_age)

        for ms in milestones:
            if _is_current(ms):
                continue  # already processed

            mt = _get("milestone_type", ms)
            amt = _get("amount", ms) or 0.0

            # Convert monthly occurrence to yearly amounts so that the DCF (yearly model) is consistent.
            if (_get("occurrence", ms) or "Yearly") == "Monthly":
                amt *= 12

            start_step = _get("age_at_occurrence", ms) - start_age
            duration = _get("duration", ms) if (_get("disbursement_type", ms) == "Fixed Duration") else None
            growth = _get("rate_of_return", ms) if _get("rate_of_return", ms) is not None else inflation_default

            if mt == "Income":
                income_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Expense":
                expense_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Asset":
                if legacy_assets_used and _get("age_at_occurrence", ms) == start_age:
                    continue
                asset_events.append((_get("age_at_occurrence", ms), amt))
            elif mt == "Liability":
                if legacy_liabs_used and _get("age_at_occurrence", ms) == start_age:
                    continue
                liability_events.append((_get("age_at_occurrence", ms), amt))

        # ------------------------------------------------------------------
        # 5. Build the DCFModel instance
        # ------------------------------------------------------------------

        if assumptions is None:
            assumptions = Assumptions(inflation=inflation_default, rate_of_return=0.08, cost_of_debt=0.06)

        return cls(
            start_age=start_age,
            end_age=end_age,
            assumptions=assumptions,
            initial_assets=current_vals["asset"],
            initial_liabilities=current_vals["liability"],
            base_salary=current_vals["income"],
            base_expenses=current_vals["expense"],
            income_streams=income_streams,
            expense_streams=expense_streams,
            asset_events=asset_events,
            liability_events=liability_events,
        )


# ────────────────────────────────────────────────────────────────────
#  Example quick-start (remove when packaging as a library)
# ────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     params = dict(
#         start_age=30,
#         end_age=40,
#         assumptions=Assumptions(inflation=0.03, rate_of_return=0.08, cost_of_debt=0.06),
#         initial_assets=50_000,
#         initial_liabilities=30_000,
#         base_salary=75_000,
#         base_expenses=60_000,
#     )
#     model = DCFModel(**params).run()
#     print(model.as_frame())
#     print(model.summary())
