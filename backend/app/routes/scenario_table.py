from flask import Blueprint, request, jsonify

from ..models.goal import Goal
from ..models.solved_parameter_value import SolvedParameterValue
from ..models.milestone import Milestone
from ..services.solver import solve_for_goal
from ..database import db

scenario_table_bp = Blueprint('scenario_table', __name__)


@scenario_table_bp.route('/api/goals', methods=['GET'])
def list_goal_parameters():
    """Return distinct parameter names that are currently flagged as goals."""
    params = (
        db.session.query(Goal.parameter)
        .filter(Goal.is_goal.is_(True))
        .distinct()
        .all()
    )
    return jsonify([p.parameter for p in params])


@scenario_table_bp.route('/api/solve', methods=['POST'])
def trigger_solver():
    """Manually trigger recalculation for a given goal parameter (optional endpoint).
    Expects JSON: { "goal": "amount" }
    """
    data = request.get_json() or {}
    goal_param = data.get('goal')
    if not goal_param:
        return jsonify({'error': 'Missing "goal"'}), 400

    milestones = Milestone.query.all()
    solve_for_goal(goal_param, milestones)
    return jsonify({'status': 'ok'})


@scenario_table_bp.route('/api/scenario-table', methods=['GET'])
def get_scenario_table():
    """Return a flat list of solved values filtered by goal parameter.
    Example response:
        [
          {
            "scenario_id": 1,
            "sub_scenario_id": 1,
            "milestone_id": 10,
            "scenario_parameter": "age_at_occurrence",
            "scenario_value": "35",
            "solved_value": 12345.67
          }, ...
        ]
    The front-end is responsible for pivoting/grouping.
    """
    goal_param = request.args.get('goal')
    if not goal_param:
        return jsonify({'error': 'Missing query parameter "goal"'}), 400

    rows = (
        db.session.query(
            SolvedParameterValue,
            Milestone.scenario_name,
            Milestone.sub_scenario_name,
            Milestone.name.label('milestone_name')
        )
        .join(Milestone, Milestone.id == SolvedParameterValue.milestone_id)
        .filter(SolvedParameterValue.goal_parameter == goal_param)
        .all()
    )

    return jsonify([{
        'scenario': row.scenario_name,
        'sub_scenario': row.sub_scenario_name,
        'milestone': row.milestone_name,
        'scenario_parameter': row.SolvedParameterValue.scenario_parameter,
        'scenario_value': row.SolvedParameterValue.scenario_value,
        'solved_value': row.SolvedParameterValue.solved_value,
    } for row in rows]) 