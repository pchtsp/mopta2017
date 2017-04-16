import mopta2017.input_data as data_import
import mopta2017.heuristics as heuristics
import mopta2017.tests as tests
import mopta2017.auxiliar as aux
import mopta2017.models as models

data_dir = "../data/20170326/"
data_in = data_import.get_data_clean(data_dir)
# solution = heuristics.initial_solution(data_in)
# sol_costs = tests.get_costs(solution, data_in)

solution = models.mip_model_complete(data_in, 1)

tests.check_solution(solution, data_in)
uncovered = tests.patients_not_covered(solution, data_in)

tests.get_job_capacity(solution, data_in, True)

job_characteristics = {job: data_in['production'][job_type] for job, job_type in solution['jobs_type'].items()}

aux.limit_start_jtype_patient(data_in)

{job: data_in['production'][job_type] for job, job_type in solution['jobs_type'].items()}

# sum(sol_costs.values())
# data_in['costs']

# tests:
# data = get_main_data(data_dir)