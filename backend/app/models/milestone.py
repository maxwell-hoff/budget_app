from datetime import datetime
from ..database import db
from sqlalchemy import Sequence, event, text

class ParentMilestone(db.Model):
    """Model representing a parent milestone that contains sub-milestones."""
    __tablename__ = 'parent_milestones'
    
    # Manually assigned high-range IDs to avoid overlap with Milestone IDs.
    # We will populate this in a SQLAlchemy "before_insert" listener below.
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

# SQLAlchemy event listener to assign ParentMilestone IDs starting at 1,000,000

# We always store ParentMilestone IDs in the range 1,000,000+ so they can never
# collide with Milestone IDs (which will start from 1).
@event.listens_for(ParentMilestone, 'before_insert')
def set_parent_milestone_id(mapper, connection, target):
    """Assign a unique ID >= 1_000_000 if one is not provided."""
    if target.id is None:
        # Initialize a class-level counter the first time we insert within this
        # application run. This guarantees uniqueness even when multiple
        # ParentMilestones are pending in the same transaction/flush.
        if not hasattr(ParentMilestone, "_next_high_id"):
            result = connection.execute(text("SELECT MAX(id) FROM parent_milestones WHERE id >= 1000000"))
            max_existing = result.scalar()
            ParentMilestone._next_high_id = 1_000_000 if max_existing is None else (max_existing + 1)

        target.id = ParentMilestone._next_high_id
        ParentMilestone._next_high_id += 1

class Milestone(db.Model):
    """Model representing a financial milestone in the timeline."""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    # Scenario grouping columns (each milestone belongs to a scenario)
    scenario_id = db.Column(db.Integer, nullable=False, default=1)
    scenario_name = db.Column(db.String(100), nullable=False, default='Base Scenario')
    # Sub-scenario grouping columns (each milestone can further belong to a sub-scenario of the parent scenario)
    sub_scenario_id = db.Column(db.Integer, nullable=False, default=1)
    sub_scenario_name = db.Column(db.String(100), nullable=False, default='Base Sub-Scenario')
    name = db.Column(db.String(100), nullable=False)
    age_at_occurrence = db.Column(db.Integer, nullable=False)
    milestone_type = db.Column(db.String(10), nullable=False, default='Expense')  # 'Income', 'Expense', 'Asset', or 'Liability'
    disbursement_type = db.Column(db.String(20), nullable=True)  # 'Fixed Duration' or 'Perpetuity'
    amount = db.Column(db.Float, nullable=False)
    payment = db.Column(db.Float, nullable=True)  # Payment amount for Assets and Liabilities
    # Value type indicators – 'PV' or 'FV' (default 'FV')
    amount_value_type = db.Column(db.String(2), nullable=False, default='FV')
    payment_value_type = db.Column(db.String(2), nullable=True, default='FV')
    occurrence = db.Column(db.String(10), nullable=True)  # 'Monthly' or 'Yearly'
    duration = db.Column(db.Integer, nullable=True)  # Duration in years
    rate_of_return = db.Column(db.Float, nullable=True)  # Rate of return as decimal
    # Optional piecewise rate-of-return schedule stored as JSON string.
    # Format: [{"x": int_offset_years, "y": decimal_rate}, ...] sorted by x.
    rate_of_return_curve = db.Column(db.Text, nullable=True)
    # --- dynamic linkage helpers -----------------------------------------
    # When *duration_end_at_milestone* is set the milestone's duration is
    # derived at runtime so the numeric ``duration`` can be NULL.
    duration_end_at_milestone = db.Column(db.String(100), nullable=True)

    # When *start_after_milestone* is set the milestone's start age is the
    # end of *another* milestone which means ``age_at_occurrence`` may be NULL.
    start_after_milestone = db.Column(db.String(100), nullable=True)
    order = db.Column(db.Integer, nullable=False, default=0)  # Order of the milestone
    parent_milestone_id = db.Column(db.Integer, db.ForeignKey('parent_milestones.id'), nullable=True)  # Reference to parent milestone
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, age_at_occurrence, milestone_type='Expense', disbursement_type=None, amount=0, payment=None, occurrence=None, duration=None, rate_of_return=None, order=0, parent_milestone_id=None,
                 scenario_id: int = 1, scenario_name: str = 'Base Scenario',
                 sub_scenario_id: int = 1, sub_scenario_name: str = 'Base Sub-Scenario',
                 duration_end_at_milestone: str | None = None,
                 start_after_milestone: str | None = None,
                 amount_value_type: str = 'FV',
                 payment_value_type: str | None = 'FV',
                  rate_of_return_curve: str | None = None,
                  ):
        self.name = name
        self.age_at_occurrence = age_at_occurrence
        self.milestone_type = milestone_type
        self.disbursement_type = disbursement_type
        self.amount = amount
        self.payment = payment
        self.amount_value_type = amount_value_type or 'FV'
        self.payment_value_type = payment_value_type or ('FV' if payment is not None else None)
        self.order = order
        self.parent_milestone_id = parent_milestone_id
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.sub_scenario_id = sub_scenario_id
        self.sub_scenario_name = sub_scenario_name
        self.rate_of_return = rate_of_return
        self.duration_end_at_milestone = duration_end_at_milestone
        self.start_after_milestone = start_after_milestone
        self.rate_of_return_curve = rate_of_return_curve
        
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
            'amount_value_type': self.amount_value_type,
            'payment_value_type': self.payment_value_type,
            'occurrence': self.occurrence,
            'duration': self.duration,
            'rate_of_return': self.rate_of_return,
            'rate_of_return_curve': self.rate_of_return_curve,
            'order': self.order,
            'parent_milestone_id': self.parent_milestone_id,
            'duration_end_at_milestone': self.duration_end_at_milestone,
            'start_after_milestone': self.start_after_milestone,
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'sub_scenario_id': self.sub_scenario_id,
            'sub_scenario_name': self.sub_scenario_name,
            'goal_parameters': [goal.parameter for goal in self.goals if goal.is_goal],
            'scenario_parameter_values': {
                param: [sv.value for sv in self.scenario_values if sv.parameter == param]
                for param in ['amount', 'age_at_occurrence', 'payment', 'occurrence', 'duration', 'rate_of_return']
                if any(sv.parameter == param for sv in self.scenario_values)
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 