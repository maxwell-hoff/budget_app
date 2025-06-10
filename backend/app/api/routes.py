from flask import Blueprint, request, jsonify
from ..database import db
from ..models.milestone import Milestone, ParentMilestone
from ..models.user import User
from ..models.net_worth import MilestoneValueByAge, NetWorthByAge
from ..models.goal import Goal
from ..models.scenario_parameter_value import ScenarioParameterValue
from ..services.dcf_calculator import DCFCalculator
from ..services.net_worth_calculator import NetWorthCalculator
from ..services.statement_parser import StatementParser
from ..services.solver import solve_for_goal
from werkzeug.utils import secure_filename
import os
from datetime import datetime

api_bp = Blueprint('api', __name__)
parser = StatementParser()

def calculate_current_age(birthday):
    """Calculate current age from birthday."""
    today = datetime.now().date()
    age = today.year - birthday.year
    if today.month < birthday.month or (today.month == birthday.month and today.day < birthday.day):
        age -= 1
    return age

def recalculate_net_worth():
    """Recalculate net worth for all milestones."""
    user = User.query.first()
    if user:
        current_age = calculate_current_age(user.birthday)
        calculator = NetWorthCalculator(current_age=current_age)
        calculator.recalculate_all()
        return True
    return False

def update_parent_milestone(parent_id):
    """Update parent milestone age range based on sub-milestones."""
    parent = ParentMilestone.query.get(parent_id)
    if parent and parent.sub_milestones:
        # Calculate min_age and max_age based on sub-milestones
        min_age = min(m.age_at_occurrence for m in parent.sub_milestones)
        max_age = min_age  # Start with min_age
        
        # Find the maximum end age considering durations
        for milestone in parent.sub_milestones:
            end_age = milestone.age_at_occurrence
            if milestone.disbursement_type == 'Fixed Duration' and milestone.duration:
                end_age += milestone.duration
            max_age = max(max_age, end_age)
        
        parent.min_age = min_age
        parent.max_age = max_age
        db.session.commit()

# -------------------------------------------------------------------------
# Goal helpers
# -------------------------------------------------------------------------

ALLOWED_GOAL_PARAMS = {
    'amount',
    'age_at_occurrence',
    'payment',
    'occurrence',
    'duration',
    'rate_of_return'
}


def sync_goal_parameters(milestone: Milestone, goal_params: list):
    """Synchronize Goal records for a milestone with the desired list of goal parameters.

    Args:
        milestone (Milestone): The milestone whose goals we are syncing.
        goal_params (list): List of parameter names that should be marked as goals.
    """
    if goal_params is None:
        return  # Nothing to sync

    # Ensure only allowed parameters are considered
    desired = {param for param in goal_params if param in ALLOWED_GOAL_PARAMS}

    # Map existing goals by parameter name for quick lookup
    existing_goals = {g.parameter: g for g in milestone.goals}

    # Add or enable desired goals
    for param in desired:
        if param in existing_goals:
            existing_goals[param].is_goal = True
        else:
            db.session.add(Goal(milestone_id=milestone.id, parameter=param, is_goal=True))

    # Remove or disable goals that are no longer desired
    for param, goal in existing_goals.items():
        if param not in desired:
            # We could soft disable by setting is_goal=False, but simpler to delete
            db.session.delete(goal)

    db.session.commit()

    # Trigger solver for each goal parameter now associated with the milestone
    for param in desired:
        solve_for_goal(param, [milestone])

@api_bp.route('/parent-milestones', methods=['GET'])
def get_parent_milestones():
    """Get all parent milestones."""
    scenario_id = request.args.get('scenario_id', type=int)
    if scenario_id is None:
        parent_milestones = ParentMilestone.query.all()
    else:
        parent_milestones = ParentMilestone.query.join(Milestone).filter(Milestone.scenario_id == scenario_id).all()
    return jsonify([milestone.to_dict() for milestone in parent_milestones])

@api_bp.route('/parent-milestones', methods=['POST'])
def create_parent_milestone():
    """Create a new parent milestone."""
    data = request.get_json()
    
    # Calculate max_age based on milestone data if provided
    max_age = data.get('max_age', data['min_age'])
    if 'milestone_data' in data:
        milestone_data = data['milestone_data']
        if milestone_data.get('disbursement_type') == 'Fixed Duration' and milestone_data.get('duration'):
            max_age = milestone_data['age_at_occurrence'] + milestone_data['duration']
    
    parent_milestone = ParentMilestone(
        name=data['name'],
        min_age=data['min_age'],
        max_age=max_age
    )
    db.session.add(parent_milestone)
    db.session.commit()
    return jsonify(parent_milestone.to_dict()), 201

@api_bp.route('/parent-milestones/<int:parent_id>', methods=['PUT'])
def update_parent_milestone_route(parent_id):
    """Update a parent milestone."""
    parent = ParentMilestone.query.get_or_404(parent_id)
    data = request.get_json()
    
    # Only update the parent milestone's own fields
    if 'name' in data:
        parent.name = data['name']
    if 'min_age' in data:
        parent.min_age = data['min_age']
    if 'max_age' in data:
        parent.max_age = data['max_age']
    
    # Ensure we're not updating any sub-milestones
    db.session.commit()
    
    # Return the updated parent milestone
    return jsonify(parent.to_dict())

@api_bp.route('/parent-milestones/<int:parent_id>', methods=['DELETE'])
def delete_parent_milestone(parent_id):
    """Delete a parent milestone and its sub-milestones."""
    parent = ParentMilestone.query.get_or_404(parent_id)
    
    # Delete all milestone values by age for each sub-milestone
    for sub_milestone in parent.sub_milestones:
        MilestoneValueByAge.query.filter_by(milestone_id=sub_milestone.id).delete()
        db.session.delete(sub_milestone)
    
    # Delete the parent milestone
    db.session.delete(parent)
    db.session.commit()
    
    # Recalculate net worth
    recalculate_net_worth()
    
    return '', 204

@api_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get the user's profile."""
    user = User.query.first()
    if user:
        return jsonify(user.to_dict())
    return jsonify({'error': 'No profile found'}), 404

@api_bp.route('/profile', methods=['POST'])
def create_profile():
    """Create or update the user's profile."""
    data = request.get_json()
    birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
    
    # Check if profile already exists
    user = User.query.first()
    if user:
        user.birthday = birthday
    else:
        user = User(birthday=birthday)
        db.session.add(user)
    
    db.session.commit()
    return jsonify(user.to_dict())

@api_bp.route('/milestones', methods=['GET'])
def get_milestones():
    """Get all milestones."""
    # Ensure inheritance amounts (and dependent values) are fresh on every fetch
    recalculate_net_worth()

    scenario_id = request.args.get('scenario_id', type=int)
    sub_scenario_id = request.args.get('sub_scenario_id', type=int)
    query = Milestone.query
    if scenario_id is not None:
        query = query.filter_by(scenario_id=scenario_id)
    if sub_scenario_id is not None:
        query = query.filter_by(sub_scenario_id=sub_scenario_id)
    milestones = query.order_by(Milestone.order).all()
    return jsonify([milestone.to_dict() for milestone in milestones])

@api_bp.route('/milestones/<int:milestone_id>/sub-milestones', methods=['GET'])
def get_sub_milestones(milestone_id):
    """Get all sub-milestones for a parent milestone."""
    sub_milestones = Milestone.query.filter_by(parent_milestone_id=milestone_id).order_by(Milestone.order).all()
    return jsonify([milestone.to_dict() for milestone in sub_milestones])

@api_bp.route('/milestones', methods=['POST'])
def create_milestone():
    """Create a new milestone."""
    data = request.get_json()
    print(f"Creating milestone with data: {data}")  # Debug log
    
    milestone = Milestone(
        name=data['name'],
        age_at_occurrence=data['age_at_occurrence'],
        milestone_type=data['milestone_type'],
        disbursement_type=data['disbursement_type'],
        amount=data['amount'],
        payment=data.get('payment'),
        occurrence=data.get('occurrence'),
        duration=data.get('duration'),
        rate_of_return=data.get('rate_of_return'),
        order=data.get('order', 0),
        parent_milestone_id=data.get('parent_milestone_id'),
        scenario_id=data.get('scenario_id', 1),
        scenario_name=data.get('scenario_name', 'Base Scenario'),
        sub_scenario_id=data.get('sub_scenario_id', 1),
        sub_scenario_name=data.get('sub_scenario_name', 'Base Sub-Scenario')
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    # Update parent milestone if this is a sub-milestone
    if milestone.parent_milestone_id:
        parent = ParentMilestone.query.get(milestone.parent_milestone_id)
        if parent:
            # Calculate max_age based on milestone duration
            max_age = milestone.age_at_occurrence
            if milestone.disbursement_type == 'Fixed Duration' and milestone.duration:
                max_age += milestone.duration
            parent.max_age = max_age
            db.session.commit()
    
    # Recalculate net worth
    recalculate_net_worth()
    
    # Sync goal parameters if provided
    if 'goal_parameters' in data:
        sync_goal_parameters(milestone, data.get('goal_parameters'))
    
    print(f"Created milestone: {milestone.to_dict()}")  # Debug log
    return jsonify(milestone.to_dict()), 201

@api_bp.route('/milestones/<int:milestone_id>', methods=['PUT'])
def update_milestone(milestone_id):
    """Update an existing milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json()
    
    # Store the old parent ID for updating
    old_parent_id = milestone.parent_milestone_id
    
    for key, value in data.items():
        # Skip goal parameters here; we'll handle separately
        if key != 'goal_parameters':
            setattr(milestone, key, value)
    
    db.session.commit()
    
    # Sync goal parameters if provided
    if 'goal_parameters' in data:
        sync_goal_parameters(milestone, data.get('goal_parameters'))
    
    # Update both old and new parent milestones if parent changed
    if old_parent_id != milestone.parent_milestone_id:
        if old_parent_id:
            update_parent_milestone(old_parent_id)
        if milestone.parent_milestone_id:
            update_parent_milestone(milestone.parent_milestone_id)
    elif milestone.parent_milestone_id:
        # Update the parent milestone's max_age based on the milestone's duration
        parent = ParentMilestone.query.get(milestone.parent_milestone_id)
        if parent:
            # Calculate max_age based on milestone's age and duration
            max_age = milestone.age_at_occurrence
            if milestone.disbursement_type == 'Fixed Duration' and milestone.duration:
                max_age += milestone.duration
            parent.max_age = max_age
            db.session.commit()
    
    # Recalculate net worth
    recalculate_net_worth()
    
    return jsonify(milestone.to_dict())

@api_bp.route('/milestones/<int:milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id):
    """Delete a milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    parent_id = milestone.parent_milestone_id
    
    # Delete all milestone values by age for this milestone
    MilestoneValueByAge.query.filter_by(milestone_id=milestone_id).delete()
    
    # If this is a sub-milestone, check if it's the last one
    if parent_id:
        parent = ParentMilestone.query.get(parent_id)
        if parent and len(parent.sub_milestones) == 1:
            # This is the last sub-milestone, delete the parent milestone
            db.session.delete(parent)
    
    db.session.delete(milestone)
    db.session.commit()
    
    # Recalculate net worth
    recalculate_net_worth()
    
    return '', 204

@api_bp.route('/calculate-dcf', methods=['POST'])
def calculate_dcf():
    """Calculate discounted cash flow for milestones."""
    # 1) Import and run the comprehensive Scenario→Sub-scenario iterator *lazily* to avoid
    #    circular import issues during application start-up.
    from backend.scripts.scenario_dcf_iterator import ScenarioDCFIterator  # type: ignore
    ScenarioDCFIterator().run()

    # 2) For now keep returning the original per-milestone PV calculation so the front-end
    #    doesn't break.  If the request body is empty we simply skip this part.

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'message': 'DCF projections recalculated for all scenarios.'})

    current_age = data.get('current_age')
    milestones = data.get('milestones', [])

    if current_age is None:
        # No traditional calculation requested – just report success.
        return jsonify({'message': 'DCF projections recalculated for all scenarios.'})

    calculator = DCFCalculator(current_age)
    results = []

    for milestone in milestones:
        if milestone.get('expense_type') == 'lump_sum':
            pv = calculator.calculate_present_value(
                milestone['amount'],
                milestone['age_at_occurrence'] - current_age
            )
        else:  # annuity
            pv = calculator.calculate_annuity_present_value(
                milestone['amount'] * 12,  # monthly → annual
                milestone['duration_years'],
                milestone['age_at_occurrence'] - current_age
            )

        results.append({'milestone_id': milestone['id'], 'present_value': pv})

    # Combine both outputs
    return jsonify({'message': 'DCF projections recalculated for all scenarios.', 'present_values': results})

@api_bp.route('/parse-statement', methods=['POST'])
def parse_statement():
    """Parse a bank statement CSV file and return the latest balance."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
        
    try:
        # Save the file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)
        
        # Parse the statement and get the latest balance
        latest_balance = parser.parse_chase_csv(filepath)
        
        # Clean up the temporary file
        os.remove(filepath)
        
        return jsonify({
            'latest_balance': latest_balance
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/net-worth', methods=['GET'])
def get_net_worth():
    """Get net worth values for all ages."""
    # Ensure net worth is calculated before returning data
    recalculate_net_worth()
    
    net_worth_values = NetWorthByAge.query.order_by(NetWorthByAge.age).all()
    return jsonify([value.to_dict() for value in net_worth_values])

@api_bp.route('/net-worth/recalculate', methods=['POST'])
def recalculate_net_worth_endpoint():
    """Recalculate net worth values."""
    if recalculate_net_worth():
        return jsonify({'message': 'Net worth recalculated successfully'})
    return jsonify({'error': 'No user profile found'}), 404

# Helper ---------------------------------------------------------------
# When a scenario parameter value is added to a milestone we want that
# value to automatically apply to *all* milestones that represent the
# same logical item across every scenario/sub-scenario.  The simplest
# heuristic is:
#   1. If this milestone belongs to a parent_milestone group, use that
#      parent_milestone_id to find all siblings.
#   2. Otherwise fall back to matching by (name, age_at_occurrence,
#      milestone_type) which is how we deduplicate milestones elsewhere
#      in the code base (see scenarios.py).
#
# This helper returns a list of IDs (including the original one).

def _get_related_milestone_ids(milestone: Milestone):
    """Return IDs of milestones that should share scenario parameter values."""
    if milestone.parent_milestone_id:
        rows = Milestone.query.filter_by(parent_milestone_id=milestone.parent_milestone_id).all()
        return [m.id for m in rows]

    # Fallback grouping when no parent_milestone_id is defined.
    rows = Milestone.query.filter_by(
        name=milestone.name,
        age_at_occurrence=milestone.age_at_occurrence,
        milestone_type=milestone.milestone_type
    ).all()
    return [m.id for m in rows]

@api_bp.route('/milestones/<int:milestone_id>/scenario-values', methods=['POST'])
def add_scenario_value(milestone_id):
    """Add a scenario parameter value for a milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json()
    parameter = data.get('parameter')
    value = data.get('value')

    if parameter not in ALLOWED_GOAL_PARAMS:
        return jsonify({'error': 'Invalid parameter'}), 400

    if value is None:
        return jsonify({'error': 'Value is required'}), 400

    value_str = str(value)

    # ------------------------------------------------------------------
    # NEW: Propagate this value to *all* related milestones.
    # ------------------------------------------------------------------
    related_ids = _get_related_milestone_ids(milestone)
    added_any = False
    for mid in related_ids:
        exists = ScenarioParameterValue.query.filter_by(
            milestone_id=mid, parameter=parameter, value=value_str
        ).first()
        if not exists:
            db.session.add(ScenarioParameterValue(milestone_id=mid, parameter=parameter, value=value_str))
            added_any = True

    if added_any:
        db.session.commit()

        # Re-solve goals for every affected milestone
        affected_milestones = Milestone.query.filter(Milestone.id.in_(related_ids)).all()
        for m in affected_milestones:
            for goal in m.goals:
                if goal.is_goal:
                    solve_for_goal(goal.parameter, [m])

        # Refresh all global goal calculations (unchanged logic)
        distinct_goal_params = {g.parameter for g in Goal.query.filter_by(is_goal=True).all()}
        all_goaled_milestones = Milestone.query.join(Goal).filter(Goal.is_goal == True).all()
        for gp in distinct_goal_params:
            solve_for_goal(gp, all_goaled_milestones)

    return jsonify(milestone.to_dict())

@api_bp.route('/milestones/<int:milestone_id>/scenario-values', methods=['DELETE'])
def delete_scenario_value(milestone_id):
    """Delete a scenario parameter value for a milestone."""
    data = request.get_json()
    parameter = data.get('parameter')
    value = data.get('value')

    if parameter not in ALLOWED_GOAL_PARAMS:
        return jsonify({'error': 'Invalid parameter'}), 400

    value_str = str(value)

    # ------------------------------------------------------------------
    # NEW: Remove this value from *all* related milestones.
    # ------------------------------------------------------------------
    related_ids = _get_related_milestone_ids(Milestone.query.get_or_404(milestone_id))
    deleted_any = False
    for mid in related_ids:
        entry = ScenarioParameterValue.query.filter_by(milestone_id=mid, parameter=parameter, value=value_str).first()
        if entry:
            db.session.delete(entry)
            deleted_any = True

    if deleted_any:
        db.session.commit()

        affected_milestones = Milestone.query.filter(Milestone.id.in_(related_ids)).all()
        for m in affected_milestones:
            for goal in m.goals:
                if goal.is_goal:
                    solve_for_goal(goal.parameter, [m])

    return jsonify(Milestone.query.get(milestone_id).to_dict())

@api_bp.route('/scenario-parameter-values', methods=['GET'])
def get_scenario_parameter_values():
    """Return distinct ScenarioParameterValue entries.

    If ?parameter=<name> is supplied, returns list for that one parameter;
    otherwise returns mapping parameter -> list(values).
    """
    param = request.args.get('parameter')
    query = ScenarioParameterValue.query
    if param is not None:
        query = query.filter_by(parameter=param)

    rows = query.all()

    if param is not None:
        values = sorted({row.value for row in rows}, key=lambda x: (str(x)))
        return jsonify(values)

    # Build mapping for all parameters
    mapping = {}
    for row in rows:
        mapping.setdefault(row.parameter, set()).add(row.value)
    mapping = {k: sorted(list(v), key=lambda x: (str(x))) for k, v in mapping.items()}
    return jsonify(mapping) 