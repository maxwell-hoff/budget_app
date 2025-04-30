from datetime import datetime
from ..database import db

class ParentMilestone(db.Model):
    """Model representing a parent milestone that contains sub-milestones."""
    __tablename__ = 'parent_milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    min_age = db.Column(db.Integer, nullable=False)
    max_age = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with sub-milestones
    sub_milestones = db.relationship('Milestone', backref='parent_milestone', lazy=True)
    
    def __init__(self, name, min_age, max_age):
        self.name = name
        self.min_age = min_age
        self.max_age = max_age
    
    def update_age_range(self):
        """Update min and max age based on sub-milestones."""
        if self.sub_milestones:
            ages = [m.age_at_occurrence for m in self.sub_milestones]
            self.min_age = min(ages)
            self.max_age = max(ages)
    
    def to_dict(self):
        """Convert parent milestone to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'min_age': self.min_age,
            'max_age': self.max_age,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Milestone(db.Model):
    """Model representing a financial milestone in the timeline."""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age_at_occurrence = db.Column(db.Integer, nullable=False)
    milestone_type = db.Column(db.String(10), nullable=False, default='Expense')  # 'Income', 'Expense', 'Asset', or 'Liability'
    disbursement_type = db.Column(db.String(20), nullable=True)  # 'Fixed Duration' or 'Perpetuity'
    amount = db.Column(db.Float, nullable=False)
    payment = db.Column(db.Float, nullable=True)  # Payment amount for Assets and Liabilities
    occurrence = db.Column(db.String(10), nullable=True)  # 'Monthly' or 'Yearly'
    duration = db.Column(db.Integer, nullable=True)  # Duration in years
    rate_of_return = db.Column(db.Float, nullable=True)  # Rate of return as decimal
    order = db.Column(db.Integer, nullable=False, default=0)  # Order of the milestone
    parent_milestone_id = db.Column(db.Integer, db.ForeignKey('parent_milestones.id'), nullable=True)  # Reference to parent milestone
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, age_at_occurrence, milestone_type='Expense', disbursement_type=None, amount=0, payment=None, occurrence=None, duration=None, rate_of_return=None, order=0, parent_milestone_id=None):
        self.name = name
        self.age_at_occurrence = age_at_occurrence
        self.milestone_type = milestone_type
        self.disbursement_type = disbursement_type
        self.amount = amount
        self.payment = payment
        self.order = order
        self.parent_milestone_id = parent_milestone_id
        
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
    
    def to_dict(self):
        """Convert milestone to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'age_at_occurrence': self.age_at_occurrence,
            'milestone_type': self.milestone_type,
            'disbursement_type': self.disbursement_type,
            'amount': self.amount,
            'payment': self.payment,
            'occurrence': self.occurrence,
            'duration': self.duration,
            'rate_of_return': self.rate_of_return,
            'order': self.order,
            'parent_milestone_id': self.parent_milestone_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 