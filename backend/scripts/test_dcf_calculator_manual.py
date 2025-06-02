# test_dcf_model.py
# --------------------------------------------------------------------
import pytest
from .dcf_calculator_manual import DCFModel, Assumptions

def test_projection_matches_reference():
    params = dict(
        start_age=30,
        end_age=40,
        assumptions=Assumptions(inflation=0.03, rate_of_return=0.08, cost_of_debt=0.06),
        initial_assets=50_000,
        initial_liabilities=30_000,
        base_salary=75_000,
        base_expenses=60_000,
    )

    expected_assets = 328_464  # reference value from the spreadsheet
    model = DCFModel(**params).run()
    result_assets = model.summary()["Ending assets balance"]
    full_dcf_table = model.as_frame()
    print(full_dcf_table)

    assert result_assets == pytest.approx(expected_assets, abs=4000)
