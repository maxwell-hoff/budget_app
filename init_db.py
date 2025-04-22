from backend.app import create_app
from backend.app.database import db
from backend.app.models.milestone import Milestone

def init_database():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add order column to existing milestones
        milestones = Milestone.query.all()
        for index, milestone in enumerate(milestones):
            milestone.order = index
        db.session.commit()
        
        print("Database initialized successfully!")

if __name__ == "__main__":
    init_database() 