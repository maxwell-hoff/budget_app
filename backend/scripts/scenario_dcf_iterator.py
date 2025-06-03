from .db_connector import DBConnector
from .dcf_calculator_manual import DCFModel, Assumptions
from app.models.dcf import DCF  # type: ignore


# ---------------------------------------------------------------------------
#  Helper functions to derive DCF inputs from milestones
# ---------------------------------------------------------------------------


def _sum_amount(milestones, m_type, age):
    """Sum *amount* for milestones of *m_type* that occur at *age*."""
    return sum(m.amount or 0 for m in milestones if m.milestone_type == m_type and m.age_at_occurrence == age)


class ScenarioDCF:
    """Handle the end-to-end DCF projection for one Scenario → Sub-scenario pair."""

    def __init__(self, db: DBConnector, scenario_id: int, sub_scenario_id: int):
        self.db = db
        self.session = db.get_session()

        data = self.db.fetch_all_data(self.session)
        self.milestones = [
            m for m in data["milestones"]
            if m.scenario_id == scenario_id and m.sub_scenario_id == sub_scenario_id
        ]

        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id

        if not self.milestones:
            raise ValueError(f"No milestones found for scenario {scenario_id}/{sub_scenario_id}")

        # — derive base inputs —
        self.start_age = min(m.age_at_occurrence for m in self.milestones)
        self.end_age = max(m.age_at_occurrence for m in self.milestones)

        self.initial_assets = _sum_amount(self.milestones, "Asset", self.start_age)
        self.initial_liabilities = _sum_amount(self.milestones, "Liability", self.start_age)
        self.base_salary = _sum_amount(self.milestones, "Income", self.start_age)
        self.base_expenses = _sum_amount(self.milestones, "Expense", self.start_age)

        # Fallbacks so that DCFModel always sees non-zero numbers
        self.initial_assets = self.initial_assets or 0.0
        self.initial_liabilities = self.initial_liabilities or 0.0
        self.base_salary = self.base_salary or 0.0
        self.base_expenses = self.base_expenses or 0.0

    # ---------------------------------------------------------------------
    #  DCF calculation & persistence
    # ---------------------------------------------------------------------

    def run(self):
        params = dict(
            start_age=self.start_age,
            end_age=self.end_age,
            assumptions=Assumptions(inflation=0.03, rate_of_return=0.08, cost_of_debt=0.06),
            initial_assets=self.initial_assets,
            initial_liabilities=self.initial_liabilities,
            base_salary=self.base_salary,
            base_expenses=self.base_expenses,
        )

        model = DCFModel(**params).run()
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


class ScenarioDCFIterator:
    """Iterates over all Scenario → Sub-scenario combinations and calculates DCFs."""

    def __init__(self):
        self.db = DBConnector()
        self.session = self.db.get_session()

    def run(self):
        data = self.db.fetch_all_data(self.session)
        combos = {
            (m.scenario_id, m.sub_scenario_id)
            for m in data["milestones"]
        }

        for scenario_id, sub_scenario_id in combos:
            sc_dcf = ScenarioDCF(self.db, scenario_id, sub_scenario_id)
            sc_dcf.run()


if __name__ == "__main__":
    ScenarioDCFIterator().run()
