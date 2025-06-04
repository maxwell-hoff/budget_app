# test_dcf_model.py
# --------------------------------------------------------------------
#  DCFModel – unit-level tests
# --------------------------------------------------------------------
# These tests purposefully avoid importing any of the database helpers so that we
# do **not** create a second SQLAlchemy instance (which previously clashed with
# the one that Flask initialises for the main app).  All calculations run purely
# in-memory.
# --------------------------------------------------------------------

from __future__ import annotations

import math

import pytest

from .dcf_calculator_manual import DCFModel, Assumptions


# --------------------------------------------------------------------
#  Pytest fixtures
# --------------------------------------------------------------------


@pytest.fixture(scope="module")
def simple_dcf_model() -> DCFModel:
    """Return a small, deterministic DCFModel instance.

    The scenario is kept intentionally short (age 30→32) so that the expected
    numbers are easy to verify by hand.  Using the public DCFModel API instead
    of going through DB-backed helpers avoids the need for a live database.
    """

    params = dict(
        start_age=30,
        end_age=32,  # 3 projection steps → 3 DataFrame rows
        assumptions=Assumptions(inflation=0.03, rate_of_return=0.05, cost_of_debt=0.04),
        initial_assets=10_000,
        initial_liabilities=5_000,
        base_salary=100_000,
        base_expenses=80_000,
    )

    return DCFModel(**params).run()


# --------------------------------------------------------------------
#  Tests
# --------------------------------------------------------------------


def test_as_frame_row_count(simple_dcf_model: DCFModel):
    """The DataFrame must contain one row per projected age."""

    df = simple_dcf_model.as_frame()
    expected_rows = (simple_dcf_model.end_age - simple_dcf_model.start_age) + 1
    assert len(df) == expected_rows


def test_salary_and_expense_growth(simple_dcf_model: DCFModel):
    """Verify that salary & expenses grow with inflation each year."""

    df = simple_dcf_model.as_frame()

    inflation = simple_dcf_model.assump.inflation
    base_salary = simple_dcf_model.income_streams[0].initial_value
    base_expense = simple_dcf_model.expense_streams[0].initial_value

    for step, row in enumerate(df.itertuples(index=False)):
        expected_salary = base_salary * (1 + inflation) ** step
        expected_expense = base_expense * (1 + inflation) ** step

        # Allow a tiny rounding error tolerance because the model rounds values
        # before storing them in the DataFrame.
        assert math.isclose(row.Salary, expected_salary, rel_tol=1e-6)
        assert math.isclose(row.Expenses, expected_expense, rel_tol=1e-6)


def test_summary_matches_internal_state(simple_dcf_model: DCFModel):
    """Ensure that summary() returns the same numbers kept in the instance."""

    summary = simple_dcf_model.summary()

    assert math.isclose(summary["Ending assets balance"], simple_dcf_model.assets[-1])
    assert math.isclose(summary["Ending liabilities"], simple_dcf_model.liabilities[-1])
    assert math.isclose(
        summary["Net worth"], simple_dcf_model.assets[-1] - simple_dcf_model.liabilities[-1]
    )
