import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


income = ctrl.Antecedent(np.arange(0, 15001, 1), 'income')
savings = ctrl.Antecedent(np.arange(0, 100001, 1), 'savings')
user_preference = ctrl.Antecedent(np.arange(0, 11, 1), 'user_preference')
risk_capacity = ctrl.Consequent(np.arange(0, 11, 1), 'risk_capacity')


income.automf(3, names=['low', 'medium', 'high'])
savings.automf(3, names=['low', 'medium', 'high'])

user_preference['low'] = fuzz.trimf(user_preference.universe, [0, 0, 5])
user_preference['medium'] = fuzz.trimf(user_preference.universe, [2, 5, 8])
user_preference['high'] = fuzz.trimf(user_preference.universe, [5, 10, 10])

risk_capacity.automf(3, names=['low', 'medium', 'high'])


rule1 = ctrl.Rule(income['low'] | savings['low'] | user_preference['low'], risk_capacity['low'])
rule2 = ctrl.Rule(income['medium'] & savings['medium'] & user_preference['medium'], risk_capacity['medium'])
rule3 = ctrl.Rule(income['high'] & savings['high'] & user_preference['high'], risk_capacity['high'])
rule4 = ctrl.Rule(income['high'] & user_preference['high'], risk_capacity['high'])


risk_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4])
risk_simulation = ctrl.ControlSystemSimulation(risk_ctrl)

def calculate_risk_profile(income: float, savings: float, user_preference: int) -> float:
    """Calculates a nuanced risk score using the fuzzy logic system."""
    try:
        risk_simulation.input['income'] = income
        risk_simulation.input['savings'] = savings
        risk_simulation.input['user_preference'] = user_preference
        
        risk_simulation.compute()
        
        return risk_simulation.output['risk_capacity']
    except Exception as e:
        print(f"Fuzzy logic error: {e}")
        return user_preference 