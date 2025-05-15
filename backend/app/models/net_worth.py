from datetime import datetime
from ..database import db

class MilestoneValueByAge(db.Model):
    """Model representing the value of a milestone at a specific age."""
    __tablename__ = 'milestone_values_by_age'
    
    id = db.Column(db.Integer, primary_key=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with Milestone
    milestone = db.relationship('Milestone', backref=db.backref('values_by_age', lazy=True))
    
    def __init__(self, milestone_id, age, value):
        self.milestone_id = milestone_id
        self.age = age
        self.value = value
    
    def to_dict(self):
        """Convert milestone value to dictionary."""
        return {
            'id': self.id,
            'milestone_id': self.milestone_id,
            'age': self.age,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class NetWorthByAge(db.Model):
    """Model representing the net worth at a specific age."""
    __tablename__ = 'net_worth_by_age'
    
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer, nullable=False, unique=True)
    net_worth = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, age, net_worth):
        self.age = age
        self.net_worth = net_worth
    
    def to_dict(self):
        """Convert net worth to dictionary."""
        return {
            'id': self.id,
            'age': self.age,
            'net_worth': self.net_worth,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class LiquidAssetsByAge(db.Model):
    """Model representing the liquid assets at a specific age."""
    __tablename__ = 'liquid_assets_by_age'
    
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer, nullable=False, unique=True)
    liquid_assets = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, age, liquid_assets):
        self.age = age
        self.liquid_assets = liquid_assets
    
    def to_dict(self):
        """Convert liquid assets to dictionary."""
        return {
            'id': self.id,
            'age': self.age,
            'liquid_assets': self.liquid_assets,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 