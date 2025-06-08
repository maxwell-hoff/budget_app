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


@pytest.fixture(scope="module")
def dcf_with_car_purchase() -> DCFModel:
    """DCF that includes a one-off car purchase two years into the horizon.

    We keep all income/expense/interest flows at *zero* so the only change to
    the asset balance stems from the purchase event.  This isolates the
    behaviour we want to test.
    """

    params = dict(
        start_age=30,
        end_age=33,  # few years to see the effect propagate
        assumptions=Assumptions(inflation=0.0, rate_of_return=0.0, cost_of_debt=0.0),
        initial_assets=50_000,
        initial_liabilities=0.0,
        base_salary=0.0,
        base_expenses=0.0,
        asset_events=[(32, -20_000)],  # car purchase at age 32
    )

    return DCFModel(**params).run()

@pytest.fixture(scope="module")
def dcf_with_car_and_retirement_purchase() -> DCFModel:
    """DCF that includes a one-off car purchase two years into the horizon.

    We keep all income/expense/interest flows at *zero* so the only change to
    the asset balance stems from the purchase event.  This isolates the
    behaviour we want to test.
    """

    params = dict(
        start_age=30,
        end_age=33,  # few years to see the effect propagate
        assumptions=Assumptions(inflation=0.0, rate_of_return=0.0, cost_of_debt=0.0),
        initial_assets=50_000,
        initial_liabilities=0.0,
        base_salary=0.0,
        base_expenses=0.0,
        asset_events=[(32, -20_000)],  # car purchase at age 32
    )

    return DCFModel(**params).run()

# --------------------------------------------------------------------
#  Milestone-driven test using the new from_milestones() helper
# --------------------------------------------------------------------


def _mock_ms(**kwargs):  # tiny helper to build dot-accessible mock milestones
    return type("MockMilestone", (), kwargs)()


@pytest.fixture(scope="module")
def dcf_from_db() -> DCFModel:
    """Build a DCF purely from mocked milestone rows (no DB involved)."""

    milestones = [
        # Opening balances & flows (current_*) --------------------------------
        _mock_ms(
            name="Current Liquid Assets",
            milestone_type="Asset",
            age_at_occurrence=30,
            disbursement_type="Perpetuity",
            amount=100_000.0,
            occurrence="Yearly",
            duration=None,
            rate_of_return=0.1,
        ),
        _mock_ms(
            name="Current Debt",
            milestone_type="Liability",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=20000.0,
            occurrence="Yearly",
            duration=4,
            rate_of_return=0.00,
        ),
        _mock_ms(
            name="Current Salary",
            milestone_type="Income",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=110_000.0,
            occurrence="Yearly",
            duration=6,  # salary stops after five years
            rate_of_return=0.04,
        ),
        _mock_ms(
            name="Current Expenses",
            milestone_type="Expense",
            age_at_occurrence=30,
            disbursement_type="Fixed Duration",
            amount=60_000.0,
            occurrence="Yearly",
            duration=6,
            rate_of_return=0.02,
        ),
        _mock_ms(
            name="Retirement",
            milestone_type="Expense",
            age_at_occurrence=36,
            disbursement_type="Fixed Duration",
            amount=55_000.0,
            occurrence="Yearly",
            duration=5,
            rate_of_return=0.02,
        )#,
        # _mock_ms(
        #     name="Inheritance",
        #     milestone_type="Asset",
        #     age_at_occurrence=40,
        #     disbursement_type="Fixed Duration",
        #     amount=100_000.0,
        #     occurrence="Yearly",
        #     duration=1,
        #     rate_of_return=None,
        # ),
    ]

    model = DCFModel.from_milestones(milestones).run()
    return model


def test_from_db_projection_runs(dcf_from_db: DCFModel):
    """Basic smoke – the DataFrame should not be empty."""

    df = dcf_from_db.as_frame()
    assert not df.empty

    # Check that age range covers exactly min→max milestone age (inclusive)
    expected_ages = set(range(int(df.Age.min()), int(df.Age.max()) + 1))
    assert set(df.Age) == expected_ages


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


def test_asset_event_applied_at_correct_age(dcf_with_car_purchase: DCFModel):
    """Beginning Assets at the event age must include the event amount."""

    df = dcf_with_car_purchase.as_frame()

    # Extract Beginning Assets for ages 30 and 32
    ba_age30 = float(df.loc[df.Age == 30, "Beginning Assets"].iloc[0])
    ba_age32 = float(df.loc[df.Age == 32, "Beginning Assets"].iloc[0])

    # The only cash-flow between 30 and 32 is the -20k event at 32, so the
    # beginning balance should step down exactly by that amount.
    expected_ba_age32 = ba_age30 - 20_000
    assert math.isclose(ba_age32, expected_ba_age32, rel_tol=1e-9), (
        f"Expected Beginning Assets at age 32 to be {expected_ba_age32:,} but got {ba_age32:,}"
    )

def test_from_db_ba_end_value(dcf_from_db: DCFModel):
    """Ending assets must match hand-calculated values."""

    df = dcf_from_db.as_frame()

    ba_age40 = float(df.loc[df.Age == 40, "Beginning Assets"].iloc[0])
    print(f"balance at age 40: {ba_age40}")
    expected_ba_age40 = 606_019 # manually calculated using a spreadsheet
    assert math.isclose(ba_age40, expected_ba_age40, rel_tol=1e-9), (
        f"Expected Beginning Assets at age 40 to be {expected_ba_age40:,} but got {ba_age40:,}"
    )

def test_from_db_le(dcf_from_db: DCFModel):
    """Ending assets must match hand-calculated values."""

    df = dcf_from_db.as_frame()

    le_age33 = float(df.loc[df.Age == 33, "Liabilities Expense"].iloc[0])
    print(df)
    print(f'full df: {df[["Age","Liabilities Expense"]]}')
    expected_le_age33 = 5_000 # manually calculated using a spreadsheet
    assert math.isclose(le_age33, expected_le_age33, rel_tol=1e-9), (
        f"Expected Liabilities Expense at age 33 to be {expected_le_age33:,} but got {le_age33:,}"
    )

def test_from_db_asset_income(dcf_from_db: DCFModel):
    """Ending assets must match hand-calculated values."""

    df = dcf_from_db.as_frame()

    assets_income_age40 = float(df.loc[df.Age == 40, "Assets Income"].iloc[0])
    print(df)
    print(f'full df: {df[["Age","Assets Income"]]}')
    expected_assets_income_age40 = 5_000 # manually calculated using a spreadsheet
    assert math.isclose(assets_income_age40, expected_assets_income_age40, rel_tol=1e-9), (
        f"Expected Liabilities Expense at age 33 to be {expected_assets_income_age40:,} but got {assets_income_age40:,}"
    )