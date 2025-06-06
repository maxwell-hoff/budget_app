# test_dcf_model.py
# --------------------------------------------------------------------
import pytest
from .db_connector import DBConnector

@pytest.fixture
def db_connector():
    return DBConnector()

def get_data(db_connector):
    sess = db_connector.get_session()
    data = db_connector.fetch_all_data(sess)
    return data

def test_scenario_calculator_connector(db_connector):
    assert db_connector is not None

def test_fetch_all_data(db_connector):
    data = get_data(db_connector)
    assert data is not None
    assert len(data) > 0

def test_milestone_data(db_connector):
    data = get_data(db_connector)
    assert len(data["milestones"][0].to_dict()) > 0

def test_scenario_data(db_connector):
    data = get_data(db_connector)
    assert data["scenario_parameter_values"] is not None
    # assert len(data["scenario_parameter_values"][0].to_dict()) > 0

def test_goal_data(db_connector):
    data = get_data(db_connector)
    assert data["goals"] is not None
    # assert len(data["goals"][0].to_dict()) > 0

def test_milestone_values_by_age_data(db_connector):
    data = get_data(db_connector)
    assert data["milestone_values_by_age"] is not None
    # assert len(data["milestone_values_by_age"][0].to_dict()) > 0
