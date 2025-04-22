from datetime import datetime
from ..database import db

class Milestone(db.Model):
    """Model representing a financial milestone in the timeline."""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age_at_occurrence = db.Column(db.Integer, nullable=False)
    milestone_type = db.Column(db.String(10), nullable=False, default='Expense')  # 'Income' or 'Expense'
    disbursement_type = db.Column(db.String(20), nullable=True)  # 'Fixed Duration' or 'Perpetuity'
    amount = db.Column(db.Float, nullable=False)
    duration_years = db.Column(db.Integer)  # Only for annuity type
    monthly_income = db.Column(db.Float)  # Only for retirement milestone
    occurrence = db.Column(db.String(10), nullable=True)  # 'Monthly' or 'Yearly'
    duration = db.Column(db.Integer, nullable=True)  # Duration in years
    rate_of_return = db.Column(db.Float, nullable=True)  # Rate of return as decimal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, age_at_occurrence, milestone_type='Expense', disbursement_type=None, amount=0, duration_years=None, monthly_income=None, occurrence=None, duration=None, rate_of_return=None):
        self.name = name
        self.age_at_occurrence = age_at_occurrence
        self.milestone_type = milestone_type
        self.disbursement_type = disbursement_type
        self.amount = amount
        
        if disbursement_type in ['Fixed Duration', 'Perpetuity']:
            self.occurrence = occurrence or 'Yearly'
            self.rate_of_return = rate_of_return or 0.0
            if disbursement_type == 'Fixed Duration':
                self.duration = duration or 1
            else:  # Perpetuity
                self.duration = None
        else:
            self.occurrence = None
            self.duration = None
            self.rate_of_return = None
        
        self.duration_years = duration_years
        self.monthly_income = monthly_income
        
    def to_dict(self):
        """Convert milestone to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'age_at_occurrence': self.age_at_occurrence,
            'milestone_type': self.milestone_type,
            'disbursement_type': self.disbursement_type,
            'amount': self.amount,
            'duration_years': self.duration_years,
            'monthly_income': self.monthly_income,
            'occurrence': self.occurrence,
            'duration': self.duration,
            'rate_of_return': self.rate_of_return,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 