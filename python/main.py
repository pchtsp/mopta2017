import mopta2017.input_data as data_import
import mopta2017.heuristics as heuristics
import mopta2017.tests as tests
import mopta2017.auxiliar as aux
import mopta2017.models as models

data_dir = "../data/20170326/"
data_in = data_import.get_data_clean(data_dir)

# Optionally, we group patients according to their proximity
data_in['demand'] = aux.group_patients(data_in=data_in, period_size=90)

# solution_2 = heuristics.initial_solution(data_in)
# sol_costs = tests.get_costs(solution_2, data_in)
# tests.check_solution(solution_2, data_in)
# solution_limit = sum(sol_costs.values())
# solution_limit = 10000

###TEMPORAL
# data_in['clients'] = {cl: name for cl, name in data_in['clients'].items() if cl in range(8)}
# data_in['demand'] = {p: data for p, data in data_in['demand'].items() if p[0] in data_in['clients'].keys()}
# data_in['sets']['vehicles'] = 4
# data_in['sets']['lines'] = 3
# data_in['production'] = data_in['production']
###TEMPORAL

# Configuration
data_in['sets']['num_routes_per_veh'] = 2
data_in['sets']['num_jobs_slowest_line'] = 3
data_in['sets']['step'] = 2
path = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results'

# solution2 = aux.load_solution(r"C:\Users\Franco\Documents\Projects\baobab\mopta2017\results\201705070923_30min_25000s.pickle")
solution = models.mip_model_complete(data_in=data_in, max_seconds=25000)
aux.export_solution(path, solution)
# solution = aux.load_solution(path + "/201705021351_3centros.pickle")

# sol_costs = tests.get_costs(solution, data_in)
# tests.check_solution(solution, data_in)
# uncovered = tests.patients_not_covered(solution, data_in)
# bad_radioactive = tests.patients_radioactive(solution, data_in)
#
# tests.get_job_capacity(solution, data_in, True)
#
# job_characteristics = {job: data_in['production'][job_type] for job, job_type in solution['jobs_type'].items()}
#
# aux.limit_start_jtype_patient(data_in)

# sum(sol_costs.values())
# data_in['costs']

# tests:
# data = get_main_data(data_dir)

solution2 = aux.load_solution(r"C:\Users\Franco\Documents\Projects\baobab\mopta2017\results\201705070923_30_todo_gurobi_25000s.pickle")
# sum(tests.get_costs(solution2, data_in).values())
#
# (sol_costs.values())
# tests.check_solution(solution, data_in)
# bad_radioactive = tests.patients_radioactive(solution, data_in)