from datetime import datetime
from ..database import db

class User(db.Model):
    """Model representing a user profile."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    birthday = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, birthday):
        self.birthday = birthday
        
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'birthday': self.birthday.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 