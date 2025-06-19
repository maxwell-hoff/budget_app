from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from pathlib import Path  # Local import to avoid polluting module scope at import time

db = SQLAlchemy()
ma = Marshmallow()

def init_db(app):
    """Initialize the database with the Flask app."""
    # ------------------------------------------------------------------
    # Use an *absolute* path for the SQLite file so that the application
    # works no matter what the current working directory is.
    # ------------------------------------------------------------------

    # The project root is two levels up from this file (backend/app → backend → project root)
    project_root = Path(__file__).resolve().parent.parent.parent

    # Ensure the instance directory exists (otherwise SQLite cannot create the DB file)
    instance_dir = project_root / 'instance'
    instance_dir.mkdir(parents=True, exist_ok=True)

    db_path = instance_dir / 'finance.db'

    # Absolute path with three leading slashes for SQLAlchemy/SQLite URI
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.as_posix()}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    ma.init_app(app)
    
    with app.app_context():
        db.create_all()

def create_default_milestones():
    """Create default milestones if none exist."""
    from .models.milestone import Milestone, ParentMilestone
    
    if not Milestone.query.first():
        # Create parent milestones for each default milestone
        current_lifestyle_parent = ParentMilestone(
            name='Current Lifestyle',
            min_age=30,  # Default age
            max_age=70  # End at retirement age
        )
        retirement_parent = ParentMilestone(
            name='Retirement',
            min_age=70,
            max_age=100  # Retirement typically lasts until end of life
        )
        long_term_care_parent = ParentMilestone(
            name='Long Term Care',
            min_age=96,
            max_age=100  # Long term care typically lasts until end of life
        )
        inheritance_parent = ParentMilestone(
            name='Inheritance',
            min_age=100,
            max_age=100  # Inheritance is a one-time event
        )
        
        # Add all parent milestones
        parents = [
            current_lifestyle_parent,
            retirement_parent,
            long_term_care_parent,
            inheritance_parent
        ]
        for parent in parents:
            db.session.add(parent)
        db.session.flush()  # Get the parent IDs
        
        # Create default milestones
        default_age = 30
        milestones = [
            Milestone(
                name='Current Liquid Assets',
                age_at_occurrence=default_age,
                milestone_type='Asset',
                disbursement_type='Perpetuity',
                amount=30000,
                payment=5000,
                occurrence='Yearly',
                duration=None,
                rate_of_return=0.07,
                order=0,
                parent_milestone_id=current_lifestyle_parent.id
            ),
            Milestone(
                name='Current Debt',
                age_at_occurrence=default_age,
                milestone_type='Liability',
                disbursement_type='Fixed Duration',
                amount=35000,
                payment=500,
                occurrence='Monthly',
                duration=120,
                rate_of_return=0.07,
                order=1,
                parent_milestone_id=current_lifestyle_parent.id
            ),
            Milestone(
                name='Current Salary (incl. Bonus, Side Hustle, etc.)',
                age_at_occurrence=default_age,
                milestone_type='Income',
                disbursement_type='Fixed Duration',
                amount=50000,
                occurrence='Yearly',
                # duration=70 - default_age,
                duration=None,  # explicit duration omitted – will be dynamic
                duration_end_at_milestone="Retirement",
                rate_of_return=0.02,
                order=2,
                parent_milestone_id=current_lifestyle_parent.id
            ),
            Milestone(
                name='Current Average Expenses',
                age_at_occurrence=default_age,
                milestone_type='Expense',
                disbursement_type='Fixed Duration',
                amount=3000,
                occurrence='Monthly',
                # duration=70 - default_age,
                duration=None,
                duration_end_at_milestone="Retirement",
                rate_of_return=0.03,
                order=3,
                parent_milestone_id=current_lifestyle_parent.id
            ),
            Milestone(
                name='Retirement',
                age_at_occurrence=70,
                milestone_type='Expense',
                disbursement_type='Fixed Duration',
                amount=60000,
                occurrence='Yearly',
                # duration=30,
                duration=None,
                duration_end_at_milestone="Inheritance",
                rate_of_return=0.06,
                order=4,
                parent_milestone_id=retirement_parent.id
            ),
            Milestone(
                name='Long Term Care (self)',
                age_at_occurrence=96,
                milestone_type='Expense',
                disbursement_type='Fixed Duration',
                amount=6000,
                occurrence='Monthly',
                duration=48,
                rate_of_return=0.04,
                order=5,
                parent_milestone_id=long_term_care_parent.id
            ),
            Milestone(
                name='Inheritance',
                age_at_occurrence=100,
                milestone_type='Expense',
                disbursement_type='Fixed Duration',
                amount=10000,
                occurrence='Monthly',
                duration=1,
                rate_of_return=0.0,
                order=6,
                parent_milestone_id=inheritance_parent.id
            )
        ]
        
        # Add all milestones
        for milestone in milestones:
            db.session.add(milestone)
        
        db.session.commit() 
        # No separate Scenario rows—milestones already seeded with scenario_id=1 