from flask import Blueprint, request, jsonify
from sqlalchemy import func

from ..database import db
from ..models.milestone import Milestone
from ..models.sub_scenario import SubScenario

sub_scenarios_bp = Blueprint('sub_scenarios', __name__)

@sub_scenarios_bp.route('/api/sub-scenarios', methods=['GET'])
def get_sub_scenarios():
    """Return all sub-scenarios for a given parent scenario (query param `scenario_id`)."""
    scenario_id = request.args.get('scenario_id', type=int)
    if scenario_id is None:
        return jsonify({'error': 'scenario_id query parameter is required'}), 400

    rows = SubScenario.query.filter_by(scenario_id=scenario_id).order_by(SubScenario.id).all()
    # Ensure every scenario always has at least one sub-scenario ("Base Sub-Scenario")
    if not rows:
        base_sub = SubScenario(scenario_id=scenario_id, name='Base Sub-Scenario')
        db.session.add(base_sub)
        db.session.commit()
        rows = [base_sub]
    return jsonify([row.to_dict() for row in rows])


@sub_scenarios_bp.route('/api/sub-scenarios', methods=['POST'])
def create_sub_scenario():
    """Create a new sub-scenario by cloning milestones of an existing sub-scenario (default base)."""
    data = request.get_json()
    name = data.get('name')
    scenario_id = data.get('scenario_id')
    # Determine the source sub-scenario to clone from (defaults to the base one for the scenario)
    source_sub_scenario_id = data.get('source_sub_scenario_id')
    if source_sub_scenario_id is None:
        base_row = SubScenario.query.filter_by(scenario_id=scenario_id).order_by(SubScenario.id).first()
        source_sub_scenario_id = base_row.id if base_row else 1  # Fallback to 1 if somehow none found

    if not name or not scenario_id:
        return jsonify({'error': 'name and scenario_id are required'}), 400

    # Create the SubScenario record first
    sub_scenario = SubScenario(scenario_id=scenario_id, name=name)
    db.session.add(sub_scenario)
    db.session.flush()  # Obtain generated ID before cloning milestones

    # Clone milestones – ensure we only copy each logical milestone once.
    source_milestones = Milestone.query.filter_by(
        scenario_id=scenario_id,
        sub_scenario_id=source_sub_scenario_id
    ).order_by(Milestone.id).all()

    ALLOWED_FIELDS = {
        'name', 'age_at_occurrence', 'milestone_type', 'disbursement_type', 'amount',
        'payment', 'occurrence', 'duration', 'rate_of_return', 'order', 'parent_milestone_id'
    }

    seen_keys = set()
    for src in source_milestones:
        # Use a tuple key that uniquely identifies a milestone irrespective of scenario-specific values.
        key = (src.name, src.age_at_occurrence, src.milestone_type, src.parent_milestone_id)
        if key in seen_keys:
            continue  # Skip duplicates that only differ in scenario-specific parameters (e.g. rate_of_return)
        seen_keys.add(key)

        params = {field: getattr(src, field) for field in ALLOWED_FIELDS}
        clone = Milestone(**params,
                          scenario_id=scenario_id,
                          scenario_name=src.scenario_name,
                          sub_scenario_id=sub_scenario.id,
                          sub_scenario_name=name)
        db.session.add(clone)

    db.session.commit()

    return jsonify(sub_scenario.to_dict()), 201


@sub_scenarios_bp.route('/api/sub-scenarios/<int:sub_scenario_id>', methods=['PUT'])
def update_sub_scenario(sub_scenario_id):
    """Rename a sub-scenario."""
    sub_scenario = SubScenario.query.get_or_404(sub_scenario_id)
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name is required'}), 400

    sub_scenario.name = name

    # Update milestones belonging to this sub-scenario
    Milestone.query.filter_by(sub_scenario_id=sub_scenario_id).update({'sub_scenario_name': name})

    db.session.commit()
    return jsonify(sub_scenario.to_dict())


@sub_scenarios_bp.route('/api/sub-scenarios/<int:sub_scenario_id>', methods=['DELETE'])
def delete_sub_scenario(sub_scenario_id):
    """Delete a sub-scenario and all associated milestones."""
    # Delete milestones first to maintain referential integrity
    Milestone.query.filter_by(sub_scenario_id=sub_scenario_id).delete()
    SubScenario.query.filter_by(id=sub_scenario_id).delete()
    db.session.commit()
    return '', 204 