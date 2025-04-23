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
            # For assets and liabilities, calculate future value
            if milestone.disbursement_type == 'Fixed Duration':
                if years_elapsed >= milestone.duration:
                    return 0.0
                    
                # Calculate remaining value based on rate of return
                if milestone.occurrence == 'Monthly':
                    rate = milestone.rate_of_return / 12
                    periods = milestone.duration * 12
                    remaining_periods = periods - (years_elapsed * 12)
                    
                    if rate == 0:
                        return milestone.amount - (milestone.payment * remaining_periods)
                    else:
                        return milestone.amount * (1 + rate) ** remaining_periods - \
                               milestone.payment * ((1 + rate) ** remaining_periods - 1) / rate
                else:  # Yearly
                    rate = milestone.rate_of_return
                    remaining_periods = milestone.duration - years_elapsed
                    
                    if rate == 0:
                        return milestone.amount - (milestone.payment * remaining_periods)
                    else:
                        return milestone.amount * (1 + rate) ** remaining_periods - \
                               milestone.payment * ((1 + rate) ** remaining_periods - 1) / rate
            else:  # Perpetuity
                if milestone.occurrence == 'Monthly':
                    rate = milestone.rate_of_return / 12
                    if rate == 0:
                        return milestone.amount
                    else:
                        return milestone.amount / rate
                else:  # Yearly
                    rate = milestone.rate_of_return
                    if rate == 0:
                        return milestone.amount
                    else:
                        return milestone.amount / rate
                        
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
    
    def update_net_worth(self):
        """Update net worth values for all ages."""
        # Clear existing net worth values
        NetWorthByAge.query.delete()
        
        # Calculate net worth for each age
        for age in range(self.current_age, self.max_age + 1):
            # Get all milestone values for this age
            milestone_values = MilestoneValueByAge.query.filter_by(age=age).all()
            
            # Calculate net worth
            net_worth = 0.0
            for value in milestone_values:
                milestone = value.milestone
                if milestone.milestone_type in ['Asset', 'Income']:
                    net_worth += value.value
                else:  # Liability or Expense
                    net_worth -= value.value
            
            # Create net worth record
            net_worth_record = NetWorthByAge(age=age, net_worth=net_worth)
            db.session.add(net_worth_record)
        
        db.session.commit()
    
    def recalculate_all(self):
        """Recalculate all milestone values and net worth."""
        self.update_milestone_values()
        self.update_net_worth() 