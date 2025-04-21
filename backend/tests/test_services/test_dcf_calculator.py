import pytest
from ..app.services.dcf_calculator import DCFCalculator

def test_calculate_present_value():
    calculator = DCFCalculator(current_age=30)
    future_value = 1000
    years_from_now = 10
    
    pv = calculator.calculate_present_value(future_value, years_from_now)
    
    # Present value should be less than future value
    assert pv < future_value
    # Present value should be positive
    assert pv > 0

def test_calculate_annuity_present_value():
    calculator = DCFCalculator(current_age=30)
    annual_amount = 12000
    years = 20
    start_year = 10
    
    pv = calculator.calculate_annuity_present_value(annual_amount, years, start_year)
    
    # Present value should be less than total payments
    assert pv < (annual_amount * years)
    # Present value should be positive
    assert pv > 0

def test_calculate_retirement_needs():
    calculator = DCFCalculator(current_age=30)
    monthly_income = 5000
    retirement_age = 65
    life_expectancy = 85
    
    pv = calculator.calculate_retirement_needs(
        monthly_income,
        retirement_age,
        life_expectancy
    )
    
    # Present value should be less than total retirement income
    total_retirement_income = monthly_income * 12 * (life_expectancy - retirement_age)
    assert pv < total_retirement_income
    # Present value should be positive
    assert pv > 0

def test_different_discount_rates():
    # Test with higher discount rate
    calculator_high = DCFCalculator(current_age=30, discount_rate=0.1)
    calculator_low = DCFCalculator(current_age=30, discount_rate=0.02)
    
    future_value = 1000
    years_from_now = 10
    
    pv_high = calculator_high.calculate_present_value(future_value, years_from_now)
    pv_low = calculator_low.calculate_present_value(future_value, years_from_now)
    
    # Higher discount rate should result in lower present value
    assert pv_high < pv_low 