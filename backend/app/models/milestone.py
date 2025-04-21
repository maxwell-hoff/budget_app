from datetime import datetime
from ..database import db

class Milestone(db.Model):
    """Model representing a financial milestone in the timeline."""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age_at_occurrence = db.Column(db.Integer, nullable=False)
    expense_type = db.Column(db.String(20), nullable=False)  # 'annuity' or 'lump_sum'
    amount = db.Column(db.Float, nullable=False)
    duration_years = db.Column(db.Integer)  # Only for annuity type
    monthly_income = db.Column(db.Float)  # Only for retirement milestone
    occurrence = db.Column(db.String(10), nullable=True)  # 'Monthly' or 'Yearly'
    duration = db.Column(db.Integer, nullable=True)  # Duration in years
    rate_of_return = db.Column(db.Float, nullable=True)  # Rate of return as decimal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, age_at_occurrence, expense_type, amount, duration_years=None, monthly_income=None, occurrence=None, duration=None, rate_of_return=None):
        self.name = name
        self.age_at_occurrence = age_at_occurrence
        self.expense_type = expense_type
        self.amount = amount
        self.duration_years = duration_years
        self.monthly_income = monthly_income
        
        # Only set these fields if it's an annuity
        if expense_type == 'annuity':
            self.occurrence = occurrence or 'Yearly'
            self.duration = duration or 1
            self.rate_of_return = rate_of_return or 0.0
        else:
            self.occurrence = None
            self.duration = None
            self.rate_of_return = None
        
    def to_dict(self):
        """Convert milestone to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'age_at_occurrence': self.age_at_occurrence,
            'expense_type': self.expense_type,
            'amount': self.amount,
            'duration_years': self.duration_years,
            'monthly_income': self.monthly_income,
            'occurrence': self.occurrence,
            'duration': self.duration,
            'rate_of_return': self.rate_of_return,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 