from flask import Blueprint, request, jsonify

from ..models.goal import Goal
from ..models.solved_parameter_value import SolvedParameterValue
from ..models.milestone import Milestone
from ..models.dcf import DCF  # baseline rows – optional for comparisons
from ..models.solved_dcf import SolvedDCF
from ..services.dcf_solver_service import run_dcf_solver
from ..database import db
import math

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
        • scenario  – scenario name for filtering
        • sub_scenario  – sub-scenario name for filtering

    The response is a flat JSON list with one entry per age-year row.
    """

    goal_param = request.args.get('goal')
    scen_param = request.args.get('scenario_parameter')
    scen_value = request.args.get('scenario_value')
    scenario_name = request.args.get('scenario')
    sub_scenario_name = request.args.get('sub_scenario')

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
    if scenario_name:
        query = query.filter(Milestone.scenario_name == scenario_name)
    if sub_scenario_name:
        query = query.filter(Milestone.sub_scenario_name == sub_scenario_name)

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


# ---------------------------------------------------------------------------
#  DCF per-age breakdown endpoint (by milestone) -----------------------------
# ---------------------------------------------------------------------------


def _compute_income_expense_breakdown_for_age(milestones: list[Milestone], *, start_age: int, target_age: int, inflation_default: float = 0.02):
    """Compute income/expense contributors for a given target_age using milestones.

    Returns two lists of dicts: (income_contribs, expense_contribs).
    """
    step = target_age - start_age
    if step < 0:
        return [], []

    # Identify base values at start_age
    base_income = sum((m.amount or 0.0) for m in milestones if m.milestone_type == 'Income' and m.age_at_occurrence == start_age)
    base_expense = sum((m.amount or 0.0) for m in milestones if m.milestone_type == 'Expense' and m.age_at_occurrence == start_age)

    def convert_occurrence_amount(m: Milestone) -> float:
        amt = m.amount or 0.0
        if (m.occurrence or 'Yearly') == 'Monthly' and m.milestone_type in ('Income', 'Expense'):
            amt *= 12
        return amt

    def effective_duration_years(m: Milestone) -> int | None:
        if m.disbursement_type != 'Fixed Duration':
            return None
        if m.duration is None:
            return None
        if (m.occurrence or 'Yearly') == 'Monthly':
            return max(int(math.ceil(m.duration / 12)), 1)
        return m.duration

    def stream_value_at(m: Milestone, at_step: int) -> float:
        start_step = m.age_at_occurrence - start_age
        if at_step < start_step:
            return 0.0
        dur = effective_duration_years(m)
        rel = at_step - start_step
        if dur is not None and rel >= dur:
            return 0.0
        initial = convert_occurrence_amount(m)
        growth = m.rate_of_return if m.rate_of_return is not None else inflation_default
        return initial * ((1 + growth) ** rel)

    income_contribs = []
    expense_contribs = []

    if base_income:
        income_contribs.append({'name': 'Current Income (base)', 'amount': base_income * ((1 + inflation_default) ** step)})
    if base_expense:
        expense_contribs.append({'name': 'Current Expenses (base)', 'amount': base_expense * ((1 + inflation_default) ** step)})

    for m in milestones:
        if m.age_at_occurrence == start_age and m.milestone_type in ('Income', 'Expense'):
            continue
        if m.milestone_type == 'Income':
            val = stream_value_at(m, step)
            if abs(val) > 1e-8:
                income_contribs.append({'name': m.name, 'amount': val})
        elif m.milestone_type == 'Expense':
            val = stream_value_at(m, step)
            if abs(val) > 1e-8:
                expense_contribs.append({'name': m.name, 'amount': val})

    income_contribs.sort(key=lambda x: abs(x['amount']), reverse=True)
    expense_contribs.sort(key=lambda x: abs(x['amount']), reverse=True)
    return income_contribs, expense_contribs


@scenario_table_bp.route('/api/dcf-breakdown', methods=['GET'])
def get_dcf_breakdown():
    """Return a breakdown of DCF components by milestone for a given age.

    Query params:
        scenario (str): Scenario name
        sub_scenario (str): Sub-scenario name
        age (int): Age/year to break down
        goal (str, optional): Goal parameter (ignored, for symmetry)
        scenario_parameter (str, optional): Name of varied parameter (ignored)
        scenario_value (str, optional): Value of varied parameter (ignored)

    Returns JSON with arrays of contributors for salary and expenses. Other
    components are currently not decomposed and are omitted for simplicity.
    """

    scenario_name = request.args.get('scenario')
    sub_scenario_name = request.args.get('sub_scenario')
    age = request.args.get('age', type=int)

    if not scenario_name or not sub_scenario_name or age is None:
        return jsonify({'error': 'scenario, sub_scenario and age are required'}), 400

    # Fetch milestones for this scenario/sub-scenario
    milestones = (
        db.session.query(Milestone)
        .filter(
            Milestone.scenario_name == scenario_name,
            Milestone.sub_scenario_name == sub_scenario_name,
        )
        .all()
    )

    if not milestones:
        return jsonify({'scenario': scenario_name, 'sub_scenario': sub_scenario_name, 'age': age, 'salary': [], 'expenses': []})

    start_age = min(m.age_at_occurrence for m in milestones)
    income_contribs, expense_contribs = _compute_income_expense_breakdown_for_age(milestones, start_age=start_age, target_age=age)

    return jsonify({
        'scenario': scenario_name,
        'sub_scenario': sub_scenario_name,
        'age': age,
        'salary': income_contribs,
        'expenses': expense_contribs,
    })


@scenario_table_bp.route('/api/dcf-breakdown-matrix', methods=['GET'])
def get_dcf_breakdown_matrix():
    """Return salary/expenses breakdown for all ages in a scenario selection.

    Query params:
        scenario, sub_scenario: names (required)
        scenario_parameter, scenario_value: optional filters to align ages with the
            selected scenario sweep used by the details table.
    """
    scenario_name = request.args.get('scenario')
    sub_scenario_name = request.args.get('sub_scenario')
    scen_param = request.args.get('scenario_parameter')
    scen_value = request.args.get('scenario_value')

    if not scenario_name or not sub_scenario_name:
        return jsonify({'error': 'scenario and sub_scenario are required'}), 400

    # Determine ages from SolvedDCF rows for consistent alignment with the table
    q = db.session.query(SolvedDCF.age).join(
        Milestone,
        (Milestone.scenario_id == SolvedDCF.scenario_id) & (Milestone.sub_scenario_id == SolvedDCF.sub_scenario_id),
    ).filter(
        Milestone.scenario_name == scenario_name,
        Milestone.sub_scenario_name == sub_scenario_name,
    )
    if scen_param:
        q = q.filter(SolvedDCF.scenario_parameter == scen_param)
    if scen_value is not None:
        q = q.filter(SolvedDCF.scenario_value == scen_value)

    ages = sorted({row.age for row in q.all()})

    # Fallback: derive ages from milestones if no solved rows found
    if not ages:
        ms_rows = (
            db.session.query(Milestone)
            .filter(
                Milestone.scenario_name == scenario_name,
                Milestone.sub_scenario_name == sub_scenario_name,
            ).all()
        )
        if not ms_rows:
            return jsonify({'scenario': scenario_name, 'sub_scenario': sub_scenario_name, 'ages': [], 'salary': {'columns': [], 'data': []}, 'expenses': {'columns': [], 'data': []}})
        start_age = min(m.age_at_occurrence for m in ms_rows)
        end_age = max((m.age_at_occurrence + (m.duration or 0)) if (m.duration and m.duration > 0) else m.age_at_occurrence for m in ms_rows)
        ages = list(range(start_age, end_age + 1))

    # Fetch milestones once and compute start_age
    ms_rows = (
        db.session.query(Milestone)
        .filter(
            Milestone.scenario_name == scenario_name,
            Milestone.sub_scenario_name == sub_scenario_name,
        ).all()
    )
    if not ms_rows:
        return jsonify({'scenario': scenario_name, 'sub_scenario': sub_scenario_name, 'ages': ages, 'salary': {'columns': [], 'data': []}, 'expenses': {'columns': [], 'data': []}})
    start_age = min(m.age_at_occurrence for m in ms_rows)

    # Build union of milestone names across all ages for salary/expenses
    salary_names = []
    expenses_names = []
    salary_set = set()
    expenses_set = set()
    per_age_salary = {}
    per_age_expenses = {}

    for a in ages:
        slist, elist = _compute_income_expense_breakdown_for_age(ms_rows, start_age=start_age, target_age=a)
        per_age_salary[a] = {item['name']: float(item['amount']) for item in slist}
        per_age_expenses[a] = {item['name']: float(item['amount']) for item in elist}
        for item in slist:
            if item['name'] not in salary_set:
                salary_set.add(item['name'])
                salary_names.append(item['name'])
        for item in elist:
            if item['name'] not in expenses_set:
                expenses_set.add(item['name'])
                expenses_names.append(item['name'])

    # Assemble matrices aligned by names order
    salary_matrix = [
        [per_age_salary.get(a, {}).get(name, 0.0) for name in salary_names]
        for a in ages
    ]
    expenses_matrix = [
        [per_age_expenses.get(a, {}).get(name, 0.0) for name in expenses_names]
        for a in ages
    ]

    return jsonify({
        'scenario': scenario_name,
        'sub_scenario': sub_scenario_name,
        'ages': ages,
        'salary': { 'columns': salary_names, 'data': salary_matrix },
        'expenses': { 'columns': expenses_names, 'data': expenses_matrix },
    })