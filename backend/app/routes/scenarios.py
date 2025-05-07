from flask import Blueprint, request, jsonify
from ..models.scenario import Scenario
from ..database import db

scenarios_bp = Blueprint('scenarios', __name__)

@scenarios_bp.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """Get all scenarios."""
    scenarios = Scenario.query.all()
    return jsonify([scenario.to_dict() for scenario in scenarios])

@scenarios_bp.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """Create a new scenario."""
    data = request.get_json()
    
    # Check if name is provided
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    # Check if name is unique
    existing = Scenario.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': 'Scenario name must be unique'}), 400
    
    # Create new scenario
    scenario = Scenario(
        name=data['name'],
        parameters=data.get('parameters', {})
    )
    
    db.session.add(scenario)
    db.session.commit()
    
    return jsonify(scenario.to_dict()), 201

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """Get a specific scenario."""
    scenario = Scenario.query.get_or_404(scenario_id)
    return jsonify(scenario.to_dict())

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    """Update a scenario."""
    scenario = Scenario.query.get_or_404(scenario_id)
    data = request.get_json()
    
    # Update parameters
    if 'parameters' in data:
        scenario.parameters = data['parameters']
    
    # Update name if provided and different
    if 'name' in data and data['name'] != scenario.name:
        # Check if new name is unique
        existing = Scenario.query.filter_by(name=data['name']).first()
        if existing and existing.id != scenario_id:
            return jsonify({'error': 'Scenario name must be unique'}), 400
        scenario.name = data['name']
    
    db.session.commit()
    return jsonify(scenario.to_dict())

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    """Delete a scenario."""
    scenario = Scenario.query.get_or_404(scenario_id)
    db.session.delete(scenario)
    db.session.commit()
    return '', 204 