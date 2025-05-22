from backend.app import create_app
from backend.app.database import db
from backend.app.models.milestone import Milestone, ParentMilestone
from sqlalchemy import text

def migrate_database():
    app = create_app()
    with app.app_context():
        # Drop existing tables to ensure clean migration
        db.drop_all()
        
        # Create tables
        db.create_all()
        
        # Drop existing sequence if it exists
        db.session.execute(text("DROP SEQUENCE IF EXISTS parent_milestone_id_seq"))
        db.session.commit()
        
        # Create the sequence starting from 1000000
        db.session.execute(text("CREATE SEQUENCE parent_milestone_id_seq START 1000000"))
        db.session.commit()
        
        # Get all milestones
        milestones = Milestone.query.all()
        
        # Create parent milestones for existing milestones
        for milestone in milestones:
            if not milestone.parent_milestone_id:
                # Create a parent milestone using the sequence
                parent = ParentMilestone(
                    name=milestone.name,
                    min_age=milestone.age_at_occurrence,
                    max_age=milestone.age_at_occurrence
                )
                db.session.add(parent)
                db.session.flush()  # Get the parent ID
                
                # Update the milestone to reference the parent
                milestone.parent_milestone_id = parent.id
        
        # Commit all changes
        db.session.commit()
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database() 