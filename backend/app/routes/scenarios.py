from flask import Blueprint, request, jsonify
from sqlalchemy import func

from ..models.milestone import Milestone
from ..database import db

scenarios_bp = Blueprint('scenarios', __name__)

@scenarios_bp.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """Return the list of distinct scenarios (id & name)."""
    rows = db.session.query(Milestone.scenario_id, Milestone.scenario_name)
    rows = rows.group_by(Milestone.scenario_id, Milestone.scenario_name).order_by(Milestone.scenario_id).all()
    scenarios = [{'id': r.scenario_id, 'name': r.scenario_name} for r in rows]
    return jsonify(scenarios)

@scenarios_bp.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """Create a new scenario by cloning provided milestones (or existing ones)."""
    data = request.get_json()

    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    # Determine next scenario_id
    max_id = db.session.query(func.max(Milestone.scenario_id)).scalar() or 1
    new_id = max_id + 1

    # If client provided milestones to start with, use them; otherwise clone milestones of scenario_id=1
    source_milestones_data = data.get('milestones')
    # Legacy support: the old API sent a 'parameters' dict with a 'milestones' key
    if source_milestones_data is None and isinstance(data.get('parameters'), dict):
        source_milestones_data = data['parameters'].get('milestones')

    if source_milestones_data is None:
        source_records = Milestone.query.filter_by(scenario_id=1).all()
        source_milestones_data = [m.to_dict() for m in source_records]

    # ------------------------------------------------------------------
    # Deduplicate: ensure we only process each source milestone once.
    # We first try to deduplicate by the provided milestone ID (if any),
    # falling back to a composite key of name + age_at_occurrence when
    # an ID is missing.  This is defensive – the frontend occasionally
    # posts the same milestone twice, which previously caused duplicates
    # in the new scenario.
    # ------------------------------------------------------------------
    unique_src = []
    seen_ids = set()
    seen_fallback_keys = set()
    for m in source_milestones_data:
        # Skip ParentMilestone entries – they live in a separate table and
        # are identified by IDs starting at 1,000,000.
        try:
            mid_val_int = int(m.get('id')) if m.get('id') is not None else None
        except (ValueError, TypeError):
            mid_val_int = None
        if mid_val_int is not None and mid_val_int >= 1_000_000:
            continue  # Ignore parent milestone forms entirely

        mid = m.get('id')
        if mid is not None:
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
        else:
            key = (m.get('name'), m.get('parameters', {}).get('age_at_occurrence') or m.get('age_at_occurrence'))
            if key in seen_fallback_keys:
                continue
            seen_fallback_keys.add(key)
        unique_src.append(m)

    # Replace the list we iterate over with the de-duplicated version
    source_milestones_data = unique_src

    # Allowed fields we can copy into a Milestone constructor
    ALLOWED_FIELDS = {
        'name','age_at_occurrence','milestone_type','disbursement_type','amount',
        'payment','occurrence','duration','rate_of_return','order','parent_milestone_id'
    }

    new_rows = []
    for m in source_milestones_data:
        base = m.get('parameters', {}) if isinstance(m, dict) else {}
        merged = {**base, **{k: v for k, v in m.items() if k != 'parameters'}}

        # If we only have an id, fetch the milestone and copy its fields
        if ('name' not in merged or 'age_at_occurrence' not in merged) and m.get('id'):
            try:
                src_id = int(m['id'])
            except (ValueError, TypeError):
                src_id = None
            src_row = Milestone.query.get(src_id) if src_id else None
            if src_row:
                merged.update({
                    'name': src_row.name,
                    'age_at_occurrence': src_row.age_at_occurrence,
                    'milestone_type': src_row.milestone_type,
                    'disbursement_type': src_row.disbursement_type,
                    'amount': src_row.amount,
                    'payment': src_row.payment,
                    'occurrence': src_row.occurrence,
                    'duration': src_row.duration,
                    'rate_of_return': src_row.rate_of_return,
                    'order': src_row.order,
                    'parent_milestone_id': src_row.parent_milestone_id
                })

        m_fields = {k: merged.get(k) for k in ALLOWED_FIELDS if merged.get(k) is not None}

        if 'name' not in m_fields or 'age_at_occurrence' not in m_fields:
            # Still malformed; skip
            continue

        new_row = Milestone(**m_fields, scenario_id=new_id, scenario_name=data['name'])
        db.session.add(new_row)
        new_rows.append(new_row)

    db.session.commit()

    return jsonify({'id': new_id, 'name': data['name']}), 201

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """Return milestones and metadata for a scenario."""
    milestones = Milestone.query.filter_by(scenario_id=scenario_id).order_by(Milestone.order).all()
    if not milestones:
        return jsonify({'error': 'Scenario not found'}), 404

    # Convert milestones into the structure the front-end expects:
    #   { id: <milestoneId>, parameters: { fieldName: value, ... } }
    ALLOWED_FIELDS = [
        'name','age_at_occurrence','milestone_type','disbursement_type','amount',
        'payment','occurrence','duration','rate_of_return','order','parent_milestone_id'
    ]

    formatted = []
    for m in milestones:
        params = {field: getattr(m, field) for field in ALLOWED_FIELDS}
        formatted.append({'id': m.id, 'parameters': params})

    scenario = {
        'id': scenario_id,
        'name': milestones[0].scenario_name,
        'milestones': formatted
    }
    return jsonify(scenario)

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    """Update scenario name or milestones (bulk)."""
    data = request.get_json()

    if 'name' in data:
        # Update name for all milestones in scenario
        Milestone.query.filter_by(scenario_id=scenario_id).update({'scenario_name': data['name']})

    if 'milestones' in data:
        for m in data['milestones']:
            row = Milestone.query.get(m.get('id'))
            if not row or row.scenario_id != scenario_id:
                continue

            params_dict = m.get('parameters', {}) if isinstance(m, dict) else {}
            merged = {**params_dict, **{k: v for k, v in m.items() if k != 'parameters'}}

            for field in ['name','age_at_occurrence','milestone_type','disbursement_type','amount','payment','occurrence','duration','rate_of_return','order','parent_milestone_id']:
                if field in merged:
                    setattr(row, field, merged[field])

    # Support legacy payloads
    if 'parameters' in data:
        pass  # Parameters blob is no longer stored; individual milestone rows already persist their values.

    db.session.commit()

    return jsonify({'id': scenario_id, 'name': data.get('name')})

@scenarios_bp.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    """Delete all milestones belonging to a scenario."""
    Milestone.query.filter_by(scenario_id=scenario_id).delete()
    db.session.commit()
    return '', 204 