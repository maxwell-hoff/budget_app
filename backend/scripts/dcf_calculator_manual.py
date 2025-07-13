# dcf_model.py
# --------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import math
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
#  Liability helper – amortising loan schedule
# ────────────────────────────────────────────────────────────────────


@dataclass
class AmortisingLoan:
    """Simple amortising (or interest-only) loan schedule."""

    principal_remaining: float
    annual_rate: float
    duration_remaining: int | float  # years; ``math.inf`` for interest-only loans
    payment: float                   # fixed periodic payment (interest + principal)

    def make_payment(self) -> tuple[float, float]:
        """Apply one payment period and return ``(total_payment, principal_repaid)``."""

        if self.principal_remaining <= 0:
            return 0.0, 0.0

        interest = self.principal_remaining * self.annual_rate

        if self.duration_remaining is math.inf:
            # Interest-only structure
            total_payment = interest
            principal_repaid = 0.0
        else:
            total_payment = self.payment
            principal_repaid = max(total_payment - interest, 0.0)
            principal_repaid = min(principal_repaid, self.principal_remaining)
            self.duration_remaining -= 1

        self.principal_remaining -= principal_repaid
        return total_payment, principal_repaid


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
        # Mapping ``age → List[Tuple[principal, custom_rate | None, duration]]``
        liability_templates: Dict[int, List[tuple]] | None = None,
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
        # Detailed loan descriptions coming from milestone parsing
        self._loan_templates: Dict[int, List[tuple]] = liability_templates or {}

        # results populated by run()
        self._table: pd.DataFrame | None = None

    # ─────────────────────── public API ─────────────────────────────
    def run(self) -> "DCFModel":
        """Iterate year-by-year to build the projection table."""

        years = self.end_age - self.start_age
        rows: List[Dict] = []

        # ── 1. Initialise loan schedules ───────────────────────────────
        active_loans: List[AmortisingLoan] = []

        def _make_loan(
            principal: float,
            rate: float,
            duration: int | None,
            payment_override: float | None = None,
        ) -> AmortisingLoan:
            """Create an *AmortisingLoan* object.

            When *payment_override* is provided we respect that fixed **annual**
            payment instead of deriving it from the usual annuity formula.  This
            allows us to honour user-entered *monthly* payment figures (×12).
            """

            if payment_override is not None:
                dur_remaining: int | float = duration if duration is not None else math.inf
                return AmortisingLoan(principal, rate, dur_remaining, payment_override)

            # ── default behaviour – derive payment from annuity math ──
            if duration is None:
                payment = principal * rate  # interest-only (per annum)
                dur_remaining = math.inf
            else:
                payment = (principal * rate) / (1 - (1 + rate) ** (-duration)) if rate else principal / duration
                dur_remaining = duration
            return AmortisingLoan(principal, rate, dur_remaining, payment)

        # Loans commencing at the projection start -----------------------
        for spec in self._loan_templates.get(self.start_age, []):
            # Support both historic 3-tuple and new 4-tuple including payment
            if len(spec) == 4:
                principal, rate_override, duration, pay_override = spec
            else:
                principal, rate_override, duration = spec
                pay_override = None

            rate = rate_override if rate_override is not None else self.assump.cost_of_debt
            active_loans.append(_make_loan(principal, rate, duration, pay_override))

        # Backwards-compatible fallback (no templates) --------------------
        if not active_loans and self.liabilities[0] > 0:
            active_loans.append(_make_loan(self.liabilities[0], self.assump.cost_of_debt, None))

        # ── 2. Projection loop ───────────────────────────────────────────
        for t in range(years + 1):
            age = self.start_age + t

            # Inject loans that start this year (skip t=0 ones already added)
            if age in self._loan_templates and (age != self.start_age or t != 0):
                for spec in self._loan_templates[age]:
                    if len(spec) == 4:
                        principal, rate_override, duration, pay_override = spec
                    else:
                        principal, rate_override, duration = spec
                        pay_override = None

                    rate = rate_override if rate_override is not None else self.assump.cost_of_debt
                    active_loans.append(_make_loan(principal, rate, duration, pay_override))

            # Beginning of year balances ---------------------------------
            a_begin_prev = self.assets[-1]
            a_begin = a_begin_prev + self._asset_events.get(age, 0.0)
            l_begin = sum(l.principal_remaining for l in active_loans)

            # Regular income / expenses ----------------------------------
            salary = sum(s.value_at(t) for s in self.income_streams)
            expenses = sum(s.value_at(t) for s in self.expense_streams)
            a_income = a_begin * self.assump.rate_of_return

            # Debt service ----------------------------------------------
            liab_expense = 0.0
            for loan in list(active_loans):  # copy -> safe removal
                payment, _ = loan.make_payment()
                liab_expense += payment
                if loan.principal_remaining <= 1e-8:
                    active_loans.remove(loan)

            # Update year-end balances -----------------------------------
            net_saving = salary - expenses - liab_expense
            a_next = a_begin + a_income + net_saving
            l_next = sum(l.principal_remaining for l in active_loans)

            if t < years:
                self.assets.append(a_next)
                self.liabilities.append(l_next)

            rows.append({
                "Age": age,
                "Beginning Assets": round(a_begin, 10),
                "Assets Income": round(a_income, 10),
                "Beginning Liabilities": round(l_begin, 10),
                "Liabilities Expense": round(liab_expense, 10),
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
            """Return *attr* from *obj* whether it is an object or a dict.

            Gracefully returns ``None`` when the attribute is missing so that
            optional fields like ``duration_end_at_milestone`` do not raise
            errors in older tests/scenarios that omit them.
            """
            if isinstance(obj, dict):
                return obj.get(attr)
            return getattr(obj, attr, None)

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
            """Return True when *ms* occurs at the projection start age.

            We treat milestones whose *effective* start age equals *start_age*
            (the earliest age across the scenario) as opening balances or
            existing income/expense streams regardless of their name.
            """
            return _effective_age(ms) == start_age and (_get("milestone_type", ms) in ("Asset", "Liability", "Income", "Expense"))

        # ------------------------------------------------------------------
        #  Dynamic duration helper  (placed early so subsequent code can use it)
        # ------------------------------------------------------------------

        # Build a quick lookup so we can find milestones by (normalised) name
        name_to_ms = { _norm_name(_get("name", m)): m for m in milestones }

        def _effective_duration(ms, _vis: set | None = None) -> int | None:
            """Return the *actual* duration handling dynamic links and cycles.

            When the duration is defined *relative* to another milestone we
            resolve that reference recursively.  If a cyclic dependency is
            detected we fall back to the milestone's stored numeric
            ``duration`` (whatever value was last entered).
            """

            if _vis is None:
                _vis = set()

            # Detect cycles using the Python object identity (unique in-memory id)
            mid = id(ms)
            if mid in _vis:
                return _get("duration", ms)  # fallback – last stored value or None

            _vis.add(mid)

            dyn_target_name = _get("duration_end_at_milestone", ms)
            if dyn_target_name:
                target_ms = name_to_ms.get(_norm_name(dyn_target_name))
                if target_ms is None:
                    raise ValueError(
                        f"Dynamic duration error: target milestone '{dyn_target_name}' not found."
                    )
                target_start_age = _effective_age(target_ms, _vis)
                own_start_age = _get("age_at_occurrence", ms)
                if own_start_age is None or target_start_age is None:
                    return _get("duration", ms)
                dur_val = max(target_start_age - own_start_age, 0)
                # Apply inheritance cap from outer scope
                if inheritance_age is not None and own_start_age is not None:
                    dur_val = min(dur_val, max(0, inheritance_age - own_start_age))
                return dur_val

            # Fallback to explicit fixed durations --------------------------------
            if (_get("disbursement_type", ms) == "Fixed Duration") and (_get("duration", ms) is not None):
                dval = _get("duration", ms)
                if inheritance_age is not None:
                    own_start_age = _get("age_at_occurrence", ms)
                    if own_start_age is not None:
                        dval = min(dval, max(0, inheritance_age - own_start_age))
                return dval

            # Perpetuity / open-ended stream --------------------------------------
            return None

        # ------------------------------------------------------------------
        #  Effective start age helper – supports dynamic "starts after" rule
        # ------------------------------------------------------------------

        def _effective_age(ms, _vis: set | None = None) -> int | None:
            """Return the age at which *ms* becomes active.

            Resolves dynamic *start-after* rules and, when a cyclic reference
            is encountered, falls back to the milestone's stored
            ``age_at_occurrence`` (last user-entered value).
            """

            if _vis is None:
                _vis = set()

            mid = id(ms)
            if mid in _vis:
                return _get("age_at_occurrence", ms)

            _vis.add(mid)

            dyn_ref_name = _get("start_after_milestone", ms)
            if dyn_ref_name:
                target = name_to_ms.get(_norm_name(dyn_ref_name))
                if target is None:
                    raise ValueError(
                        f"Dynamic age error: reference milestone '{dyn_ref_name}' not found."
                    )
                target_start = _effective_age(target, _vis)
                dur = _effective_duration(target, _vis) or 0
                if target_start is None:
                    return _get("age_at_occurrence", ms)
                return target_start + dur

            return _get("age_at_occurrence", ms)

        # ------------------------------------------------------------------
        # 2. Derive projection horizon – stop at inheritance age when present
        # ------------------------------------------------------------------

        ages = [_effective_age(m) for m in milestones]
        if not ages:
            raise ValueError("No milestones supplied – cannot build DCF model.")

        start_age = min(ages)

        # Detect "inheritance" milestone which acts as death marker
        inh_ms_list = [m for m in milestones if _norm_name(_get("name", m)) == "inheritance"]
        inheritance_age = _get("age_at_occurrence", inh_ms_list[0]) if inh_ms_list else None

        end_candidates = []
        for m in milestones:
            dur_val = _effective_duration(m)
            eff_start = _effective_age(m)
            if dur_val and dur_val > 0:
                cand = eff_start + dur_val
            else:
                cand = eff_start
            end_candidates.append(cand)

        end_age = max(end_candidates)

        # Clamp horizon at inheritance age when defined
        if inheritance_age is not None:
            end_age = min(end_age, inheritance_age)

        # ------------------------------------------------------------------
        # 3. Prepare containers for streams & balances
        # ------------------------------------------------------------------

        income_streams: List[GrowingSeries] = []
        expense_streams: List[GrowingSeries] = []
        asset_events: List[tuple[int, float]] = []
        liability_events: List[tuple[int, float]] = []  # kept for backwards-compat

        current_vals: Dict[str, float] = {"asset": 0.0, "liability": 0.0}

        # Flags for fallback behaviour and containers ---------------------
        current_income_found = False
        current_expense_found = False

        # Track rate_of_return on 'current' asset milestones so we can
        # override the global asset growth assumption when provided.
        asset_roi_data: List[tuple[float, float]] = []  # (amount, roi)

        # Detailed liability descriptors (age → list[(principal, roi_override, duration)])
        from collections import defaultdict
        liability_templates: Dict[int, List[tuple]] = defaultdict(list)

        for ms in milestones:
            if not _is_current(ms):
                continue

            # ----------------------------------------------------------------
            # Map the milestone to one of the four opening balance/flow groups.
            # Prefer the explicit mapping first; otherwise fall back to the
            # milestone_type which already matches the desired group key.
            # ----------------------------------------------------------------
            norm = _norm_name(_get("name", ms))
            key = _CURRENT_MAP.get(norm)
            if key is None:
                key = (_get("milestone_type", ms) or "").lower()
            current_vals[key] += _get("amount", ms) or 0.0

            roi_val = _get("rate_of_return", ms)
            if roi_val is not None:
                asset_roi_data.append((_get("amount", ms) or 0.0, roi_val))
            elif key == "income":
                current_income_found = True
                amt = _get("amount", ms) or 0.0
                duration = _effective_duration(ms)
                growth = _get("rate_of_return", ms) if _get("rate_of_return", ms) is not None else inflation_default
                income_streams.append(GrowingSeries(amt, growth, start_step=0, duration=duration))
            elif key == "expense":
                current_expense_found = True
                amt = _get("amount", ms) or 0.0
                duration = _effective_duration(ms)
                growth = _get("rate_of_return", ms) if _get("rate_of_return", ms) is not None else inflation_default
                expense_streams.append(GrowingSeries(amt, growth, start_step=0, duration=duration))

        # Fallback to legacy behaviour if explicit current_* milestones are absent
        def _sum_amount(m_type, age):
            return sum(
                (_get("amount", x) or 0.0)
                for x in milestones
                if (_get("milestone_type", x) == m_type and _effective_age(x) == age)
            )

        if current_vals.get("asset", 0.0) == 0.0:
            current_vals["asset"] = _sum_amount("Asset", start_age)
        if current_vals.get("liability", 0.0) == 0.0:
            current_vals["liability"] = 0.0

        base_salary = 0.0
        base_expenses = 0.0

        if not current_income_found:
            base_salary = _sum_amount("Income", start_age)
        if not current_expense_found:
            base_expenses = _sum_amount("Expense", start_age)

        # ------------------------------------------------------------------
        # 4. Convert remaining milestones → streams / events
        # ------------------------------------------------------------------

        legacy_assets_used = current_vals["asset"] == _sum_amount("Asset", start_age)
        legacy_liabs_used = current_vals["liability"] == _sum_amount("Liability", start_age)

        for ms in milestones:
            if _is_current(ms):
                continue  # already processed

            mt = _get("milestone_type", ms)
            amt = _get("amount", ms) or 0.0

            # Convert *monthly* figures to *yearly* equivalents **only** for
            # Income/Expense streams.  Asset or Liability amounts are one-off
            # principal balances and must NOT be multiplied.
            if (_get("occurrence", ms) or "Yearly") == "Monthly" and mt in ("Income", "Expense"):
                amt *= 12

            start_step = _effective_age(ms) - start_age
            duration = _effective_duration(ms)
            growth = _get("rate_of_return", ms) if _get("rate_of_return", ms) is not None else inflation_default

            if mt == "Income":
                income_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Expense":
                expense_streams.append(GrowingSeries(amt, growth, start_step=start_step, duration=duration))
            elif mt == "Asset":
                if legacy_assets_used and _effective_age(ms) == start_age:
                    continue
                asset_events.append((_effective_age(ms), amt))
            elif mt == "Liability":
                # Build amortising loan template ---------------------------
                age_at = _effective_age(ms)
                principal = amt  # principal balance stays exactly as entered

                duration_ms = _effective_duration(ms)
                rate_override = _get("rate_of_return", ms)

                # ------------------------------------------------------------------
                # Convert *monthly* parameters → yearly equivalents
                # ------------------------------------------------------------------
                payment_override = None
                if (_get("occurrence", ms) or "Yearly") == "Monthly":
                    # Duration     : months → years
                    if duration_ms is not None:
                        duration_ms = max(int(math.ceil(duration_ms / 12)), 1)

                    # Payment field: monthly → annual figure (for override)
                    pay_val = _get("payment", ms)
                    if pay_val is not None:
                        payment_override = pay_val * 12
                else:
                    pay_val = _get("payment", ms)
                    if pay_val is not None:
                        payment_override = pay_val  # already annual

                liability_templates[age_at].append((principal, rate_override, duration_ms, payment_override))

        # ------------------------------------------------------------------
        # 5. Build the DCFModel instance
        # ------------------------------------------------------------------

        if assumptions is None:
            # If at least one current asset milestone specified a rate_of_return
            # compute the weighted average across the supplied opening balances.
            if asset_roi_data:
                total_amt = sum(a for a, _ in asset_roi_data)
                weighted_roi = sum(a * r for a, r in asset_roi_data) / total_amt if total_amt else 0.0
                asset_return = weighted_roi
            else:
                asset_return = 0.08  # legacy default

            assumptions = Assumptions(inflation=inflation_default, rate_of_return=asset_return, cost_of_debt=0.06)

        # (model build moved below so we can attach liability interest ranges)

        # ------------------------------------------------------------------
        # 6. Mark years with active liability interest so that run() can skip
        #    payments once the duration ends.
        # ------------------------------------------------------------------

        liab_years: set[int] = set()
        for ms in milestones:
            if _get("milestone_type", ms) == "Liability" and _effective_duration(ms):
                start = _effective_age(ms)
                liab_years.update(range(start, start + _effective_duration(ms)))

        model: "DCFModel" = cls(
            start_age=start_age,
            end_age=end_age,
            assumptions=assumptions,
            initial_assets=current_vals["asset"],
            initial_liabilities=current_vals["liability"],
            base_salary=base_salary,
            base_expenses=base_expenses,
            income_streams=income_streams,
            expense_streams=expense_streams,
            asset_events=asset_events,
            liability_events=liability_events,
            liability_templates=liability_templates,
        )

        model._liab_interest_years = liab_years
        return model


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
