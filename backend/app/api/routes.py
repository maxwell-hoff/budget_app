from flask import Blueprint, request, jsonify
from ..database import db
from ..models.milestone import Milestone
from ..services.dcf_calculator import DCFCalculator
from ..services.statement_parser import StatementParser

api_bp = Blueprint('api', __name__)

@api_bp.route('/milestones', methods=['GET'])
def get_milestones():
    """Get all milestones."""
    milestones = Milestone.query.all()
    return jsonify([milestone.to_dict() for milestone in milestones])

@api_bp.route('/milestones', methods=['POST'])
def create_milestone():
    """Create a new milestone."""
    data = request.get_json()
    
    milestone = Milestone(
        name=data['name'],
        age_at_occurrence=data['age_at_occurrence'],
        expense_type=data['expense_type'],
        amount=data['amount'],
        duration_years=data.get('duration_years'),
        monthly_income=data.get('monthly_income')
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify(milestone.to_dict()), 201

@api_bp.route('/milestones/<int:milestone_id>', methods=['PUT'])
def update_milestone(milestone_id):
    """Update an existing milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json()
    
    for key, value in data.items():
        setattr(milestone, key, value)
    
    db.session.commit()
    return jsonify(milestone.to_dict())

@api_bp.route('/milestones/<int:milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id):
    """Delete a milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    db.session.delete(milestone)
    db.session.commit()
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
    """Parse a bank statement CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    parser = StatementParser()
    
    try:
        transactions = parser.parse_chase_csv(file)
        balance_sheet = parser.calculate_balance_sheet(transactions)
        return jsonify(balance_sheet)
    except Exception as e:
        return jsonify({'error': str(e)}), 400 