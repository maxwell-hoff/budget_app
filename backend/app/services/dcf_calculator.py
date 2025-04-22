import numpy as np
from datetime import datetime

class DCFCalculator:
    """Service for performing discounted cash flow calculations."""
    
    def __init__(self, current_age, inflation_rate=0.02, discount_rate=0.05):
        """
        Initialize the DCF calculator.
        
        Args:
            current_age (int): Current age of the user
            inflation_rate (float): Expected annual inflation rate
            discount_rate (float): Discount rate for present value calculations
        """
        self.current_age = current_age
        self.inflation_rate = inflation_rate
        self.discount_rate = discount_rate
    
    def calculate_present_value(self, future_value, years_from_now):
        """
        Calculate the present value of a future amount.
        
        Args:
            future_value (float): The future amount
            years_from_now (int): Number of years until the amount is needed
            
        Returns:
            float: Present value of the future amount
        """
        return future_value / ((1 + self.discount_rate) ** years_from_now)
    
    def calculate_annuity_present_value(self, annual_amount, years, start_year):
        """
        Calculate the present value of an annuity.
        
        Args:
            annual_amount (float): Annual payment amount
            years (int): Number of years the annuity will last
            start_year (int): Number of years until the annuity starts
            
        Returns:
            float: Present value of the annuity
        """
        # Calculate the present value of the annuity at the start date
        pv_at_start = annual_amount * (1 - (1 + self.discount_rate) ** -years) / self.discount_rate
        
        # Discount back to present value
        return pv_at_start / ((1 + self.discount_rate) ** start_year)
    
    def calculate_retirement_needs(self, monthly_income, retirement_age, life_expectancy):
        """
        Calculate the present value of retirement needs.
        
        Args:
            monthly_income (float): Desired monthly income during retirement
            retirement_age (int): Age at retirement
            life_expectancy (int): Expected age at death
            
        Returns:
            float: Present value of retirement needs
        """
        years_until_retirement = retirement_age - self.current_age
        retirement_duration = life_expectancy - retirement_age
        annual_amount = monthly_income * 12
        
        return self.calculate_annuity_present_value(
            annual_amount,
            retirement_duration,
            years_until_retirement
        ) 