from flask import Blueprint, request, jsonify
from ..database import db
from ..models.milestone import Milestone, ParentMilestone
from ..models.user import User
from ..models.net_worth import MilestoneValueByAge, NetWorthByAge
from ..services.dcf_calculator import DCFCalculator
from ..services.net_worth_calculator import NetWorthCalculator
from ..services.statement_parser import StatementParser
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
    """Update parent milestone name and age range based on sub-milestones."""
    parent = ParentMilestone.query.get(parent_id)
    if parent and parent.sub_milestones:
        # If there's only one sub-milestone, use its name
        if len(parent.sub_milestones) == 1:
            parent.name = parent.sub_milestones[0].name
        # Update age range
        parent.update_age_range()
        db.session.commit()

@api_bp.route('/parent-milestones', methods=['GET'])
def get_parent_milestones():
    """Get all parent milestones."""
    parent_milestones = ParentMilestone.query.all()
    return jsonify([milestone.to_dict() for milestone in parent_milestones])

@api_bp.route('/parent-milestones', methods=['POST'])
def create_parent_milestone():
    """Create a new parent milestone."""
    data = request.get_json()
    parent_milestone = ParentMilestone(
        name=data['name'],
        min_age=data['min_age'],
        max_age=data['max_age']
    )
    db.session.add(parent_milestone)
    db.session.commit()
    return jsonify(parent_milestone.to_dict()), 201

@api_bp.route('/parent-milestones/<int:parent_id>', methods=['PUT'])
def update_parent_milestone_route(parent_id):
    """Update a parent milestone."""
    parent = ParentMilestone.query.get_or_404(parent_id)
    data = request.get_json()
    
    for key, value in data.items():
        setattr(parent, key, value)
    
    db.session.commit()
    return jsonify(parent.to_dict())

@api_bp.route('/parent-milestones/<int:parent_id>', methods=['DELETE'])
def delete_parent_milestone(parent_id):
    """Delete a parent milestone and its sub-milestones."""
    parent = ParentMilestone.query.get_or_404(parent_id)
    
    # Delete all sub-milestones
    for sub_milestone in parent.sub_milestones:
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
    milestones = Milestone.query.order_by(Milestone.order).all()
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
        parent_milestone_id=data.get('parent_milestone_id')
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    # Update parent milestone if this is a sub-milestone
    if milestone.parent_milestone_id:
        update_parent_milestone(milestone.parent_milestone_id)
    
    # Recalculate net worth
    recalculate_net_worth()
    
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
        setattr(milestone, key, value)
    
    db.session.commit()
    
    # Update both old and new parent milestones if parent changed
    if old_parent_id != milestone.parent_milestone_id:
        if old_parent_id:
            update_parent_milestone(old_parent_id)
        if milestone.parent_milestone_id:
            update_parent_milestone(milestone.parent_milestone_id)
    
    # Recalculate net worth
    recalculate_net_worth()
    
    return jsonify(milestone.to_dict())

@api_bp.route('/milestones/<int:milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id):
    """Delete a milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    parent_id = milestone.parent_milestone_id
    
    db.session.delete(milestone)
    db.session.commit()
    
    # Update parent milestone if this was a sub-milestone
    if parent_id:
        update_parent_milestone(parent_id)
    
    # Recalculate net worth
    recalculate_net_worth()
    
    return '', 204

@api_bp.route('/calculate-dcf', methods=['POST'])
def calculate_dcf():
    """Calculate discounted cash flow for milestones."""
    data = request.get_json()
    current_age = data['current_age']
    milestones = data['milestones']
    
    calculator = DCFCalculator(current_age)
    results = []
    
    for milestone in milestones:
        if milestone['expense_type'] == 'lump_sum':
            pv = calculator.calculate_present_value(
                milestone['amount'],
                milestone['age_at_occurrence'] - current_age
            )
        else:  # annuity
            pv = calculator.calculate_annuity_present_value(
                milestone['amount'] * 12,  # Convert monthly to annual
                milestone['duration_years'],
                milestone['age_at_occurrence'] - current_age
            )
        
        results.append({
            'milestone_id': milestone['id'],
            'present_value': pv
        })
    
    return jsonify(results)

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