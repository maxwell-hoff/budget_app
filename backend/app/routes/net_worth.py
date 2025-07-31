from flask import Blueprint, jsonify
from ..models.net_worth import NetWorthByAge
from ..services.net_worth_calculator import NetWorthCalculator
from ..models.user import User
from datetime import datetime
from ..models.milestone import Milestone
from ..models.solved_dcf import SolvedDCF
from sqlalchemy import func
from ..models.scenario import Scenario
from ..models.sub_scenario import SubScenario
from ..database import db

net_worth_bp = Blueprint('net_worth', __name__)

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

@net_worth_bp.route('/api/net-worth', methods=['GET'])
def get_net_worth():
    """Get net worth values for all ages."""
    # Ensure net worth is recalculated
    calculator = NetWorthCalculator(current_age=30)  # TODO: Get current age from user settings
    calculator.recalculate_all()
    
    # Get net worth values
    net_worth_values = NetWorthByAge.query.order_by(NetWorthByAge.age).all()
    
    return jsonify([value.to_dict() for value in net_worth_values])

@net_worth_bp.route('/api/liquid-assets', methods=['GET'])
def get_liquid_assets():
    """Get liquid assets values for all ages."""
    # Ensure net worth is recalculated
    calculator = NetWorthCalculator(current_age=30)  # TODO: Get current age from user settings
    calculator.recalculate_all()
    
    # Get all ages from net worth values
    net_worth_values = NetWorthByAge.query.order_by(NetWorthByAge.age).all()
    
    # Calculate liquid assets for each age
    liquid_assets_values = []
    for net_worth in net_worth_values:
        liquid_assets = calculator.calculate_liquid_assets_at_age(net_worth.age)
        liquid_assets_values.append({
            'age': net_worth.age,
            'liquid_assets': liquid_assets
        })
    
    return jsonify(liquid_assets_values)

@net_worth_bp.route('/api/liquidity', methods=['GET'])
def get_liquidity():
    """Get liquidity values for all ages."""
    # Ensure net worth is recalculated
    calculator = NetWorthCalculator(current_age=30)  # TODO: Get current age from user settings
    calculator.recalculate_all()
    
    # Get all ages from net worth values
    net_worth_values = NetWorthByAge.query.order_by(NetWorthByAge.age).all()
    
    # Calculate liquid assets for each age
    liquid_assets_values = []
    for net_worth in net_worth_values:
        liquid_assets = calculator.calculate_liquid_assets_at_age(net_worth.age)
        liquid_assets_values.append({
            'age': net_worth.age,
            'liquid_assets': liquid_assets
        })
    
    return jsonify(liquid_assets_values) 

# ---------------------------------------------------------------------------
#  NEW ENDPOINTS – scenario-level net-worth projections
# ---------------------------------------------------------------------------

@net_worth_bp.route('/api/net-worth-range', methods=['GET'])
def get_net_worth_range():
    """Return the min / max net-worth across *all* scenario combinations for every age.

    Aggregates data from the `SolvedDCF` table instead of the summary
    `NetWorthByAge` table so that every scenario/sub-scenario/parameter sweep is
    included in the calculation.
    """
    # Use SQL aggregation to compute min/max net-worth per age directly in the DB
    net_expr = (
        (SolvedDCF.beginning_assets + SolvedDCF.assets_income)
        - (SolvedDCF.beginning_liabilities + SolvedDCF.liabilities_expense)
        + (SolvedDCF.salary - SolvedDCF.expenses)
    )

    rows = (
        db.session
        .query(
            SolvedDCF.age.label('age'),
            func.min(net_expr).label('min_net_worth'),
            func.max(net_expr).label('max_net_worth'),
        )
        .group_by(SolvedDCF.age)
        .order_by(SolvedDCF.age)
        .all()
    )

    return jsonify([
        {
            'age': row.age,
            'min_net_worth': row.min_net_worth,
            'max_net_worth': row.max_net_worth,
        }
        for row in rows
    ])


@net_worth_bp.route('/api/net-worth-line', methods=['GET'])
def get_net_worth_line():
    """Return the net-worth projection line for a single scenario/sub-scenario.

    Query params:
        scenario (str): Scenario *name* (unique)
        sub_scenario (str): Sub-scenario *name*
        scenario_parameter (str, optional)
        scenario_value (str, optional)
        scenario_id (int, optional)
        sub_scenario_id (int, optional)
    """
    from flask import request  # local import to avoid circular issues

    scenario_name = request.args.get('scenario')
    sub_scenario_name = request.args.get('sub_scenario')
    # Name or ID params ----------------------------------------------------
    scenario_id = request.args.get('scenario_id', type=int)
    sub_scenario_id = request.args.get('sub_scenario_id', type=int)

    param_filter = request.args.get('scenario_parameter')
    value_filter = request.args.get('scenario_value')

    # Resolve scenario & sub IDs ------------------------------------------
    if scenario_id and sub_scenario_id:
        scenario = Scenario.query.get(scenario_id)
        sub_scenario = SubScenario.query.get(sub_scenario_id)
        if not scenario or not sub_scenario:
            return jsonify({'error': 'Scenario or sub-scenario ID not found'}), 404
    else:
        if not scenario_name or not sub_scenario_name:
            return jsonify({'error': 'scenario/sub_scenario (or ids) required'}), 400

        scenario = Scenario.query.filter_by(name=scenario_name).first()
        if not scenario:
            return jsonify({'error': f'Scenario "{scenario_name}" not found'}), 404

        sub_scenario = (
            SubScenario.query
            .filter_by(name=sub_scenario_name, scenario_id=scenario.id)
            .first()
        )
        if not sub_scenario:
            return jsonify({'error': f'Sub-scenario "{sub_scenario_name}" not found'}), 404

    # Build expression (same as for range) ----------------------------------
    net_expr = (
        (SolvedDCF.beginning_assets + SolvedDCF.assets_income)
        - (SolvedDCF.beginning_liabilities + SolvedDCF.liabilities_expense)
        + (SolvedDCF.salary - SolvedDCF.expenses)
    )

    rows = (
        db.session
        .query(SolvedDCF.age.label('age'), net_expr.label('net_worth'))
        .filter(
            SolvedDCF.scenario_id == scenario.id,
            SolvedDCF.sub_scenario_id == sub_scenario.id,
            *(
                [SolvedDCF.scenario_parameter == param_filter] if param_filter else []
            ),
            *(
                [SolvedDCF.scenario_value == value_filter] if value_filter else []
            ),
        )
        .order_by(SolvedDCF.age)
        .all()
    )

    return jsonify([{ 'age': r.age, 'net_worth': r.net_worth } for r in rows])

# ---------------------------------------------------------------------------
#  Monte Carlo range endpoint ------------------------------------------------
# ---------------------------------------------------------------------------
from backend.app.models.monte_carlo_dcf import MonteCarloDCF

@net_worth_bp.route('/api/net-worth-mc-range', methods=['GET'])
def get_mc_net_worth_range():
    """Return min/max net-worth values from Monte Carlo best/worst paths.

    Accepts the same query parameters as /api/net-worth-line
    (scenario/sub_scenario identifiers plus optional scenario_parameter/value).
    """
    from flask import request
    scenario_name = request.args.get('scenario')
    sub_scenario_name = request.args.get('sub_scenario')
    scenario_id = request.args.get('scenario_id', type=int)
    sub_scenario_id = request.args.get('sub_scenario_id', type=int)
    param_filter = request.args.get('scenario_parameter')
    value_filter = request.args.get('scenario_value')

    # Resolve scenario/sub IDs identical to line endpoint ------------------
    if scenario_id and sub_scenario_id:
        scenario = Scenario.query.get(scenario_id)
        sub_scenario = SubScenario.query.get(sub_scenario_id)
        if not scenario or not sub_scenario:
            return jsonify({'error': 'Scenario or sub-scenario ID not found'}), 404
    else:
        if not scenario_name or not sub_scenario_name:
            return jsonify({'error': 'scenario/sub_scenario (or ids) required'}), 400
        scenario = Scenario.query.filter_by(name=scenario_name).first()
        if not scenario:
            return jsonify({'error': f'Scenario "{scenario_name}" not found'}), 404
        sub_scenario = (
            SubScenario.query
            .filter_by(name=sub_scenario_name, scenario_id=scenario.id)
            .first()
        )
        if not sub_scenario:
            return jsonify({'error': f'Sub-scenario "{sub_scenario_name}" not found'}), 404

    # Build net-worth expression -----------------------------------------
    net_expr = (
        (MonteCarloDCF.beginning_assets + MonteCarloDCF.assets_income)
        - (MonteCarloDCF.beginning_liabilities + MonteCarloDCF.liabilities_expense)
        + (MonteCarloDCF.salary - MonteCarloDCF.expenses)
    )

    # Query both result_types and pivot in Python so we always have aligned ages
    rows = (
        db.session
        .query(
            MonteCarloDCF.age.label('age'),
            MonteCarloDCF.result_type.label('result_type'),
            net_expr.label('net_worth'),
        )
        .filter(
            MonteCarloDCF.scenario_id == scenario.id,
            MonteCarloDCF.sub_scenario_id == sub_scenario.id,
            *([MonteCarloDCF.scenario_parameter == param_filter] if param_filter else []),
            *([MonteCarloDCF.scenario_value == value_filter] if value_filter else []),
        )
        .order_by(MonteCarloDCF.age)
        .all()
    )

    data_by_age = {}
    for r in rows:
        d = data_by_age.setdefault(r.age, {'age': r.age, 'min_net_worth': None, 'max_net_worth': None})
        if r.result_type == 'min':
            d['min_net_worth'] = r.net_worth
        elif r.result_type == 'max':
            d['max_net_worth'] = r.net_worth

    # Keep only ages that have both min & max values available
    result = [d for d in data_by_age.values() if d['min_net_worth'] is not None and d['max_net_worth'] is not None]
    result.sort(key=lambda x: x['age'])
    return jsonify(result)
