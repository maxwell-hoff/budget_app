from flask import Blueprint, jsonify
from ..models.net_worth import NetWorthByAge, LiquidAssetsByAge
from ..services.net_worth_calculator import NetWorthCalculator
from ..models.user import User
from datetime import datetime
from ..models.milestone import Milestone

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
    
    # Get liquid assets values
    liquid_assets_values = LiquidAssetsByAge.query.order_by(LiquidAssetsByAge.age).all()
    
    return jsonify([value.to_dict() for value in liquid_assets_values])

@net_worth_bp.route('/api/liquidity', methods=['GET'])
def get_liquidity():
    """Get liquidity values for all ages."""
    # Ensure net worth is recalculated
    calculator = NetWorthCalculator(current_age=30)  # TODO: Get current age from user settings
    calculator.recalculate_all()
    
    # Get liquid assets values
    liquid_assets_values = LiquidAssetsByAge.query.order_by(LiquidAssetsByAge.age).all()
    
    # Log the data being returned
    print("Liquidity data:", [value.to_dict() for value in liquid_assets_values])
    
    # Check if there are any milestones
    milestones = Milestone.query.all()
    print("Number of milestones:", len(milestones))
    print("Milestones:", [m.to_dict() for m in milestones])
    
    return jsonify([value.to_dict() for value in liquid_assets_values]) 