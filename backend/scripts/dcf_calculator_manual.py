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
    """A geometric series—e.g., salary growing with inflation."""
    initial_value: float
    growth_rate: float

    def value_at(self, step: int) -> float:
        return self.initial_value * (1 + self.growth_rate) ** step


# ────────────────────────────────────────────────────────────────────
#  Main DCF engine
# ────────────────────────────────────────────────────────────────────
class DCFModel:
    """
    Finite-horizon, yearly projection that mirrors ‘Budget Test.xlsx’.

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
        base_salary: float,
        base_expenses: float,
    ):
        # ── store scenario settings ────────────────────────────────
        self.start_age = start_age
        self.end_age = end_age
        self.assump = assumptions

        # ── cash-flow drivers ──────────────────────────────────────
        self.salary_stream = GrowingSeries(base_salary, self.assump.inflation)
        self.expense_stream = GrowingSeries(base_expenses, self.assump.inflation)

        # ── state variables over time ──────────────────────────────
        self.assets:  List[float] = [initial_assets]
        self.liabilities: List[float] = [initial_liabilities]

        # results populated by run()
        self._table: pd.DataFrame | None = None

    # ─────────────────────── public API ─────────────────────────────
    def run(self) -> "DCFModel":
        """Iterates year by year and fills the internal DataFrame."""
        years = self.end_age - self.start_age
        rows: List[Dict] = []

        for t in range(years + 1):
            age = self.start_age + t
            a_begin = self.assets[-1]
            l_begin = self.liabilities[-1]

            # yearly flows
            salary = self.salary_stream.value_at(t)
            expenses = self.expense_stream.value_at(t)
            a_income = a_begin * self.assump.rate_of_return
            l_interest = l_begin * self.assump.cost_of_debt      # also equals principal repayment

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
        self.extra_income = stream


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
