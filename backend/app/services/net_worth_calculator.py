from ..database import db
from ..models.milestone import Milestone
from ..models.net_worth import MilestoneValueByAge, NetWorthByAge
from datetime import datetime
import math

# ---------------------------------------------------------------------------
#  Utility helpers
# ---------------------------------------------------------------------------

def _safe_pow(base: float, exp: int | float) -> float:
    """Compute ``base ** exp`` but clamp to `float('inf')` on overflow.

    This prevents extremely large scenario parameters (e.g. very long durations)
    from blowing up the net-worth calculation with an OverflowError.
    """
    try:
        return base ** exp
    except OverflowError:
        return float("inf")

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
                dur_lim = milestone.duration if milestone.duration is not None else math.inf
                if years_elapsed >= dur_lim:
                    return 0.0
                    
                # Calculate remaining balance based on rate of return
                if milestone.occurrence == 'Monthly':
                    rate = milestone.rate_of_return / 12
                    periods = (milestone.duration or dur_lim) * 12
                    remaining_periods = periods - (years_elapsed * 12)
                    
                    if rate == 0:
                        balance = milestone.amount - (milestone.payment or 0) * remaining_periods
                    else:
                        comp = _safe_pow(1 + rate, remaining_periods)
                        balance = milestone.amount * comp - (milestone.payment or 0) * (comp - 1) / rate
                    
                    # For liabilities, ensure balance doesn't go negative
                    if milestone.milestone_type == 'Liability':
                        return max(0, balance)
                    return balance
                else:  # Yearly
                    rate = milestone.rate_of_return
                    remaining_periods = (milestone.duration or dur_lim) - years_elapsed
                    
                    if rate == 0:
                        balance = milestone.amount - (milestone.payment or 0) * remaining_periods
                    else:
                        comp = _safe_pow(1 + rate, remaining_periods)
                        balance = milestone.amount * comp - (milestone.payment or 0) * (comp - 1) / rate
                    
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
                        comp = _safe_pow(1 + rate, periods)
                        balance = milestone.amount * comp - payment * (comp - 1) / rate
                else:  # Yearly
                    rate = milestone.rate_of_return
                    periods = years_elapsed
                    payment = milestone.payment or 0
                    
                    if rate == 0:
                        balance = milestone.amount - payment * periods
                    else:
                        comp = _safe_pow(1 + rate, periods)
                        balance = milestone.amount * comp - payment * (comp - 1) / rate
                
                # For liabilities, ensure balance doesn't go negative
                if milestone.milestone_type == 'Liability':
                    return max(0, balance)
                return balance
                        
        elif milestone.milestone_type in ['Income', 'Expense']:
            # For income and expenses, calculate cumulative impact
            if milestone.disbursement_type == 'Fixed Duration':
                dur_lim = milestone.duration if milestone.duration is not None else math.inf
                if years_elapsed >= dur_lim:
                    return 0.0
                    
                # Calculate cumulative impact
                if milestone.occurrence == 'Monthly':
                    value = milestone.amount * 12 * years_elapsed
                else:  # Yearly
                    value = milestone.amount * years_elapsed
            else:  # Perpetuity
                if milestone.occurrence == 'Monthly':
                    value = milestone.amount * 12 * years_elapsed
                else:  # Yearly
                    value = milestone.amount * years_elapsed

            # Expenses reduce liquid assets, so make them negative
            if milestone.milestone_type == 'Expense':
                value = -value

            return value
    
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
        liquid_assets = 0.0
        for mv in milestone_values:
            mt = mv.milestone.milestone_type
            if mt == 'Asset':
                liquid_assets += mv.value
            elif mt == 'Liability':
                # liabilities are ignored for liquid-assets metric
                continue
            else:  # Income or Expense values already carry sign (+ / -)
                liquid_assets += mv.value
        
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
            
            # Calculate asset and liability values
            for milestone_value in milestone_values:
                milestone = milestone_value.milestone
                mt_type = milestone.milestone_type
                if mt_type == 'Asset':
                    current_liquid_assets += milestone_value.value
                elif mt_type == 'Liability':
                    current_debt += milestone_value.value
                else:  # Income or Expense
                    current_liquid_assets += milestone_value.value
            
            # Calculate net worth
            net_worth = current_liquid_assets - current_debt
            
            # Create net worth record
            net_worth_record = NetWorthByAge(age=age, net_worth=net_worth)
            db.session.add(net_worth_record)
        
        db.session.commit()
    
    def update_inheritance_amounts(self):
        """Synchronise the amount of every "Inheritance" milestone to equal the
        liquid assets *excluding that inheritance* at its age of occurrence.

        This is run after an initial milestone-value refresh so that the
        MilestoneValueByAge table has up-to-date balances we can query.
        """
        # Gather every milestone that represents an inheritance event
        inheritance_milestones = Milestone.query.filter(Milestone.name == 'Inheritance').all()
        if not inheritance_milestones:
            return  # Nothing to do

        for inh_ms in inheritance_milestones:
            target_age = inh_ms.age_at_occurrence

            # Sum liquid assets (Asset-type milestones) **at target_age** for the same
            # scenario & sub-scenario, explicitly excluding the inheritance milestone
            assets_query = (
                MilestoneValueByAge.query
                .join(Milestone, MilestoneValueByAge.milestone_id == Milestone.id)
                .filter(
                    MilestoneValueByAge.age == target_age,
                    Milestone.milestone_type == 'Asset',
                    Milestone.id != inh_ms.id,  # exclude the inheritance itself
                    Milestone.scenario_id == inh_ms.scenario_id,
                    Milestone.sub_scenario_id == inh_ms.sub_scenario_id,
                )
            )
            liquid_assets = sum(row.value for row in assets_query.all())

            # Update the inheritance amount only if it differs to avoid needless writes
            if inh_ms.amount != liquid_assets:
                inh_ms.amount = liquid_assets

        # Persist any updates so that the next milestone-value calculation sees them
        db.session.commit()
    
    def recalculate_all(self):
        """Recalculate milestone values, inheritance amounts and net worth."""
        # 1. Initial milestone value refresh (based on current stored data)
        self.update_milestone_values()

        # 2. Update inheritance amounts to mirror liquid assets at their age
        self.update_inheritance_amounts()

        # 3. Re-compute milestone values so inherited amounts are reflected
        self.update_milestone_values()

        # 4. Finally compute net worth using the refreshed milestone values
        self.update_net_worth() 