"""
milestone_calculator.py
======================
Standalone script for calculating milestone values by age.

This script provides a template for implementing your own milestone value calculations.
It includes all necessary database connections and helper functions to read/write data.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add the parent directory to sys.path so we can import from app
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.milestone import Milestone
from app.models.net_worth import MilestoneValueByAge
from app.models.goal import Goal
from app.models.scenario_parameter_value import ScenarioParameterValue
from app.database import db
from app import create_app

class MilestoneCalculator:
    """Base class for milestone value calculations."""
    
    def __init__(
        self,
        data: Dict[str, List],
        scenario_id: int,
        sub_scenario_id: int,
        min_age: int = 30,
        max_age: int = 100
    ):
        """
        Initialize the calculator.
        
        Args:
            data: Dictionary containing all necessary data (milestones, goals, etc.)
            scenario_id: ID of the scenario to calculate for
            sub_scenario_id: ID of the sub-scenario to calculate for
            min_age: Minimum age to calculate values for
            max_age: Maximum age to calculate values for
        """
        self.data = data
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        self.min_age = min_age
        self.max_age = max_age
        self.all_ages = list(range(min_age, max_age + 1))

    def calculate_milestone_value(self, milestone: Milestone, age: int) -> float:
        """
        Calculate the value of a milestone at a specific age.
        
        Args:
            milestone: The milestone to calculate value for
            age: The age to calculate the value at
            
        Returns:
            float: The calculated value
        """
        # TODO: Implement your calculation logic here
        # This is where you'll put your custom calculation logic
        return 0.0

    def calculate_all_milestone_values(self) -> List[Dict]:
        """
        Calculate values for all milestones at all ages.
        
        Returns:
            List[Dict]: List of records to be inserted into milestone_values_by_age
        """
        records = []
        for milestone in self.data["milestones"]:
            for age in self.all_ages:
                value = self.calculate_milestone_value(milestone, age)
                records.append({
                    "milestone_id": milestone.id,
                    "age": age,
                    "value": value
                })
        return records

def get_session() -> Session:
    """Return a SQLAlchemy session bound to the configured database."""
    app: Flask = create_app()
    engine = create_engine(db.engine.url)
    SessionFactory = sessionmaker(bind=engine)
    return SessionFactory()

def fetch_all_data(session: Session, scenario_id: Optional[int] = None) -> Dict[str, List]:
    """Fetch raw data from the database."""
    milestone_query = session.query(Milestone)
    if scenario_id is not None:
        milestone_query = milestone_query.filter(Milestone.scenario_id == scenario_id)
    milestones = milestone_query.all()

    milestone_ids = [m.id for m in milestones] if scenario_id is not None else None

    goals_query = session.query(Goal)
    spv_query = session.query(ScenarioParameterValue)
    mva_query = session.query(MilestoneValueByAge)

    if milestone_ids is not None:
        goals_query = goals_query.filter(Goal.milestone_id.in_(milestone_ids))
        spv_query = spv_query.filter(ScenarioParameterValue.milestone_id.in_(milestone_ids))
        mva_query = mva_query.filter(MilestoneValueByAge.milestone_id.in_(milestone_ids))

    return {
        "milestones": milestones,
        "milestone_values_by_age": mva_query.all(),
        "goals": goals_query.all(),
        "scenario_parameter_values": spv_query.all(),
    }

def upsert_milestone_values(session: Session, records: List[Dict]) -> None:
    """Insert or update milestone values in the database."""
    for rec in records:
        obj = (
            session.query(MilestoneValueByAge)
            .filter_by(milestone_id=rec["milestone_id"], age=rec["age"])
            .first()
        )

        if obj is None:
            obj = MilestoneValueByAge(**rec)
        else:
            obj.value = rec["value"]

        session.add(obj)

    session.commit()

if __name__ == "__main__":
    # Example usage
    session = get_session()
    data = fetch_all_data(session, scenario_id=1)
    
    # Create your calculator instance
    calculator = MilestoneCalculator(data, scenario_id=1, sub_scenario_id=1)
    
    # Calculate all values
    records = calculator.calculate_all_milestone_values()
    
    # Save to database
    upsert_milestone_values(session, records) 