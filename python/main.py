import mopta2017.input_data as data_import
import mopta2017.heuristics as heuristics
import mopta2017.tests as tests

data_dir = "../data/20170326/"
data_in = data_import.get_data_clean(data_dir)
solution = heuristics.initial_solution(data_in)
sol_costs = tests.get_costs(solution, data_in)

# sum(sol_costs.values())
# data_in['costs']

# tests:
# data = get_main_data(data_dir)