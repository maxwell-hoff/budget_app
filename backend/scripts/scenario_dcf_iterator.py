from db_connector import DBConnector
from dcf_calculator_manual import DCFModel, Assumptions


class ScenarioDCF:
    def __init__(self, scenario_id, sub_scenario_id):
        db_connector = DBConnector()
        sess = db_connector.get_session()
        self.data = db_connector.fetch_all_data(sess)    
        self.scenario_id = scenario_id
        self.sub_scenario_id = sub_scenario_id
        

    def get_scenario_milestones(self):
        self.scenario_milestones = []
        for milestone in self.data["milestones"]:
            if milestone["scenario_id"] == self.scenario_id and milestone["sub_scenario_id"] == self.sub_scenario_id:
                self.scenario_milestones.append(milestone)

    def get_scenario_min_max_age(self):
        self.min_age = min(self.data["milestones"], key=lambda x: x['age'])['age']
        self.max_age = max(self.data["milestone_values_by_age"], key=lambda x: x['age'])['age']
    
    def get_initial_assets(self):
        pass

    def get_initial_liabilities(self):
        pass

    def get_base_salary(self):
        pass

    def get_base_expenses(self):
        pass

    def get_dcf_parameters(self):
        self.get_scenario_milestones()
        self.get_scenario_min_max_age()
        self.get_initial_assets()
        self.get_initial_liabilities()


    def model_dcf(self):
        params = dict(
            start_age=self.start_age,
            end_age=self.end_age,
            assumptions=Assumptions(inflation=0.03, rate_of_return=0.08, cost_of_debt=0.06),
            initial_assets=50_000,
            initial_liabilities=30_000,
            base_salary=75_000,
            base_expenses=60_000,
        )

        self.model = DCFModel(**params).run()
        full_dcf_table = self.model.as_frame()
        print(full_dcf_table)
    
    def write_dcf_to_db(self):
        pass

class ScenarioDCFIterator(ScenarioDCF):
    def __init__(self):
        super().__init__()
    
    def get_all_scenario_sub_scenarios_combinations(self):
        for milestone in self.data["milestones"]:
            milestone['scenario']
        
    def dcf_iterator(self, write_to_db=True):
        min_age, max_age = self.get_min_max_age()
        for age in range(min_age, max_age + 1):
            self.model_dcf(age)
            if write_to_db:
                self.write_dcf_to_db(age)
    
    def scenario_dcf_iterator(self):
        for scenario in self.data["scenario_parameter_values"]:
            self.dcf_iterator(scenario, write_to_db=True)
    


if __name__ == "__main__":
    scenario_dcf_iterator = ScenarioDCFIterator()
    scenario_dcf_iterator.get_all_scenario_sub_scenarios_combinations()
