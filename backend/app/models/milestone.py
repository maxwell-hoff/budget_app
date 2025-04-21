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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, age_at_occurrence, expense_type, amount, duration_years=None, monthly_income=None):
        self.name = name
        self.age_at_occurrence = age_at_occurrence
        self.expense_type = expense_type
        self.amount = amount
        self.duration_years = duration_years
        self.monthly_income = monthly_income
        
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
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 