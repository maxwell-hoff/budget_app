from flask import Blueprint, request, jsonify

from ..models.goal import Goal
from ..models.solved_parameter_value import SolvedParameterValue
from ..models.milestone import Milestone
from ..models.dcf import DCF  # baseline rows – optional for comparisons
from ..models.solved_dcf import SolvedDCF
from ..services.dcf_solver_service import run_dcf_solver
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
    """Manually trigger recalculation of solved parameters using the
    DCF-based solver backend.  The request payload may include an optional
    ``goal`` field but the DCF solver currently recomputes *all* goal
    parameters flagged in the database, so the field is accepted only
    for backwards-compatibility.
    """

    # Accept and ignore legacy payload structure so existing front-ends
    # continue to work without changes.
    _ = request.get_json() or {}

    # Kick off the solver – it will (up-)insert rows into
    # ``solved_parameter_values`` *and* ``solved_dcf``.
    run_dcf_solver()

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


# ---------------------------------------------------------------------------
#  New helper – expose solved DCF projection rows
# ---------------------------------------------------------------------------


@scenario_table_bp.route('/api/solved-dcf', methods=['GET'])
def get_solved_dcf():
    """Return solved DCF projection rows.

    Optional query parameters allow for light filtering:
        • goal  – goal parameter (e.g. "amount")
        • scenario_parameter  – parameter that was varied (e.g. "age_at_occurrence")
        • scenario_value      – concrete value of the scenario parameter

    The response is a flat JSON list with one entry per age-year row.
    """

    goal_param = request.args.get('goal')
    scen_param = request.args.get('scenario_parameter')
    scen_value = request.args.get('scenario_value')

    query = db.session.query(
        SolvedDCF,
        Milestone.scenario_name,
        Milestone.sub_scenario_name,
    ).join(
        Milestone,
        (Milestone.scenario_id == SolvedDCF.scenario_id) & (Milestone.sub_scenario_id == SolvedDCF.sub_scenario_id),
    )

    if goal_param:
        query = query.filter(SolvedDCF.goal_parameter == goal_param)
    if scen_param:
        query = query.filter(SolvedDCF.scenario_parameter == scen_param)
    if scen_value is not None:
        query = query.filter(SolvedDCF.scenario_value == scen_value)

    rows = query.order_by(
        SolvedDCF.scenario_id,
        SolvedDCF.sub_scenario_id,
        SolvedDCF.scenario_parameter,
        SolvedDCF.scenario_value,
        SolvedDCF.age,
    ).all()

    return jsonify([
        {
            'scenario': r.scenario_name,
            'sub_scenario': r.sub_scenario_name,
            'goal_parameter': r.SolvedDCF.goal_parameter,
            'scenario_parameter': r.SolvedDCF.scenario_parameter,
            'scenario_value': r.SolvedDCF.scenario_value,
            'age': r.SolvedDCF.age,
            'beginning_assets': r.SolvedDCF.beginning_assets,
            'assets_income': r.SolvedDCF.assets_income,
            'beginning_liabilities': r.SolvedDCF.beginning_liabilities,
            'liabilities_expense': r.SolvedDCF.liabilities_expense,
            'salary': r.SolvedDCF.salary,
            'expenses': r.SolvedDCF.expenses,
        }
        for r in rows
    ]) 