from ..database import db
from ..models.milestone import Milestone
from ..models.net_worth import MilestoneValueByAge, NetWorthByAge
from datetime import datetime

class NetWorthCalculator:
    """Service for calculating net worth values over time."""
    
    def __init__(self, current_age, max_age=100):
        """
        Initialize the net worth calculator.
        
        Args:
            current_age (int): Current age of the user
            max_age (int): Maximum age to calculate net worth for
        """
        self.current_age = current_age
        self.max_age = max_age
    
    def calculate_milestone_value_at_age(self, milestone, target_age):
        """
        Calculate the value of a milestone at a specific age.
        
        Args:
            milestone (Milestone): The milestone to calculate value for
            target_age (int): The age to calculate the value at
            
        Returns:
            float: The value of the milestone at the target age
        """
        if target_age < milestone.age_at_occurrence:
            return 0.0
            
        years_elapsed = target_age - milestone.age_at_occurrence
        
        if milestone.milestone_type in ['Asset', 'Liability']:
            # For assets and liabilities, calculate remaining balance
            if milestone.disbursement_type == 'Fixed Duration':
                if years_elapsed >= milestone.duration:
                    return 0.0
                    
                # Calculate remaining balance based on rate of return
                if milestone.occurrence == 'Monthly':
                    rate = milestone.rate_of_return / 12
                    periods = milestone.duration * 12
                    remaining_periods = periods - (years_elapsed * 12)
                    
                    if rate == 0:
                        balance = milestone.amount - (milestone.payment or 0) * remaining_periods
                    else:
                        # Calculate remaining balance
                        balance = milestone.amount * (1 + rate) ** remaining_periods - \
                                (milestone.payment or 0) * ((1 + rate) ** remaining_periods - 1) / rate
                    
                    # For liabilities, ensure balance doesn't go negative
                    if milestone.milestone_type == 'Liability':
                        return max(0, balance)
                    return balance
                else:  # Yearly
                    rate = milestone.rate_of_return
                    remaining_periods = milestone.duration - years_elapsed
                    
                    if rate == 0:
                        balance = milestone.amount - (milestone.payment or 0) * remaining_periods
                    else:
                        # Calculate remaining balance
                        balance = milestone.amount * (1 + rate) ** remaining_periods - \
                                (milestone.payment or 0) * ((1 + rate) ** remaining_periods - 1) / rate
                    
                    # For liabilities, ensure balance doesn't go negative
                    if milestone.milestone_type == 'Liability':
                        return max(0, balance)
                    return balance
            else:  # Perpetuity
                # For perpetuity, calculate balance with rate of return and payments
                if milestone.occurrence == 'Monthly':
                    rate = milestone.rate_of_return / 12
                    periods = years_elapsed * 12
                    payment = milestone.payment or 0
                    
                    if rate == 0:
                        balance = milestone.amount - payment * periods
                    else:
                        # Calculate balance with compound interest and regular payments
                        balance = milestone.amount * (1 + rate) ** periods - \
                                payment * ((1 + rate) ** periods - 1) / rate
                else:  # Yearly
                    rate = milestone.rate_of_return
                    periods = years_elapsed
                    payment = milestone.payment or 0
                    
                    if rate == 0:
                        balance = milestone.amount - payment * periods
                    else:
                        # Calculate balance with compound interest and regular payments
                        balance = milestone.amount * (1 + rate) ** periods - \
                                payment * ((1 + rate) ** periods - 1) / rate
                
                # For liabilities, ensure balance doesn't go negative
                if milestone.milestone_type == 'Liability':
                    return max(0, balance)
                return balance
                        
        elif milestone.milestone_type in ['Income', 'Expense']:
            # For income and expenses, calculate cumulative impact
            if milestone.disbursement_type == 'Fixed Duration':
                if years_elapsed >= milestone.duration:
                    return 0.0
                    
                # Calculate cumulative impact
                if milestone.occurrence == 'Monthly':
                    return milestone.amount * 12 * years_elapsed
                else:  # Yearly
                    return milestone.amount * years_elapsed
            else:  # Perpetuity
                if milestone.occurrence == 'Monthly':
                    return milestone.amount * 12 * years_elapsed
                else:  # Yearly
                    return milestone.amount * years_elapsed
    
    def update_milestone_values(self):
        """Update milestone values for all ages."""
        milestones = Milestone.query.all()
        
        # Clear existing milestone values
        MilestoneValueByAge.query.delete()
        
        # Calculate and store values for each milestone at each age
        for milestone in milestones:
            for age in range(self.current_age, self.max_age + 1):
                value = self.calculate_milestone_value_at_age(milestone, age)
                milestone_value = MilestoneValueByAge(
                    milestone_id=milestone.id,
                    age=age,
                    value=value
                )
                db.session.add(milestone_value)
        
        db.session.commit()
    
    def calculate_liquid_assets_at_age(self, age):
        """
        Calculate liquid assets at a specific age from milestone values.
        
        Args:
            age (int): The age to calculate liquid assets for
            
        Returns:
            float: The liquid assets at the specified age
        """
        # Get all milestone values for this age
        milestone_values = MilestoneValueByAge.query.filter_by(age=age).all()
        
        # Sum up all asset values
        liquid_assets = sum(
            milestone_value.value 
            for milestone_value in milestone_values 
            if milestone_value.milestone.milestone_type == 'Asset'
        )
        
        return liquid_assets
    
    def update_net_worth(self):
        """Update net worth values for all ages."""
        # Clear existing net worth values
        NetWorthByAge.query.delete()
        
        # Calculate net worth for each age
        for age in range(self.current_age, self.max_age + 1):
            # Initialize current liquid assets and debt
            current_liquid_assets = 0.0
            current_debt = 0.0
            
            # Get all milestone values for this age
            milestone_values = MilestoneValueByAge.query.filter_by(age=age).all()
            
            # First pass: Calculate asset and liability values
            for milestone_value in milestone_values:
                milestone = milestone_value.milestone
                if milestone.milestone_type in ['Asset', 'Liability']:
                    if milestone.milestone_type == 'Asset':
                        current_liquid_assets += milestone_value.value
                    else:  # Liability
                        current_debt += milestone_value.value
            
            # Second pass: Calculate income/expense impact
            for milestone_value in milestone_values:
                milestone = milestone_value.milestone
                if milestone.milestone_type in ['Income', 'Expense']:
                    if milestone.milestone_type == 'Income':
                        current_liquid_assets += milestone_value.value
                    else:  # Expense
                        if current_liquid_assets >= milestone_value.value:
                            current_liquid_assets -= milestone_value.value
                        else:
                            # If expenses exceed liquid assets, add excess to debt
                            excess = milestone_value.value - current_liquid_assets
                            current_liquid_assets = 0
                            current_debt += excess
            
            # Calculate net worth
            net_worth = current_liquid_assets - current_debt
            
            # Create net worth record
            net_worth_record = NetWorthByAge(age=age, net_worth=net_worth)
            db.session.add(net_worth_record)
        
        db.session.commit()
    
    def recalculate_all(self):
        """Recalculate all milestone values and net worth."""
        self.update_milestone_values()
        self.update_net_worth() 