import mopta2017.input_data as data_import
import mopta2017.heuristics as heuristics
import mopta2017.tests as tests
import mopta2017.auxiliar as aux
import mopta2017.models as models
import pickle

data_dir = "../data/20170326/"
data_in = data_import.get_data_clean(data_dir)

# Optionally, we group patients according to their proximity
data_in['demand'] = aux.group_patients(data_in=data_in, period_size=30)

solution_2 = heuristics.initial_solution(data_in)
sol_costs = tests.get_costs(solution_2, data_in)
tests.check_solution(solution_2, data_in)
solution_limit = sum(sol_costs.values())
solution_limit = 10000
solution = models.mip_model_complete(data_in=data_in, max_seconds=5000, cutoff=solution_limit)
sol_costs = tests.get_costs(solution, data_in)
tests.check_solution(solution, data_in)
uncovered = tests.patients_not_covered(solution, data_in)
bad_radioactive = tests.patients_radioactive(solution, data_in)

tests.get_job_capacity(solution, data_in, True)

job_characteristics = {job: data_in['production'][job_type] for job, job_type in solution['jobs_type'].items()}

aux.limit_start_jtype_patient(data_in)

# sum(sol_costs.values())
# data_in['costs']

# tests:
# data = get_main_data(data_dir)

if False:
    path = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results\solution_instance6.pickle'

    with open(path, 'wb') as f:
        pickle.dump(solution, f)

    with open(path, 'rb') as f:
        # The protocol version used is detected automatically, so we do not
        # have to specify it.
        data = pickle.load(f)