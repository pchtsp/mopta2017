import os
import mopta2017.auxiliar as aux
import mopta2017.tests as tests
import re
import mopta2017.input_data as data_import
import csv

def time_from_name(name):
    result = re.search('_p(\d*)', name)
    if result is not None:
        return result.group(1)

data_directory = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results'
data_directory_2 = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results2'
files_list = [name for name in os.listdir(data_directory) if os.path.splitext(name)[1] == ".pickle"]
files_names = [os.path.splitext(name)[0] for name in files_list]
files_paths = {files_names[key]: os.path.join(data_directory, file) for key, file in enumerate(files_list)}
# files_paths = { '201706190051_p60_t40000_scbc_tight': 'C:\\Users\\Franco\\Documents\\Projects\\baobab\\mopta2017\\results\\201706190051_p60_t40000_scbc_tight.pickle'}
file_data = {}
for name, path in files_paths.items():
    with open(path, 'r') as f:
        try:
            file_data[name] = aux.load_solution(path)
        except:
            print(path + ": bad format")

periods = {key: time_from_name(key) for key in file_data.keys()}

data_dir = "../data/20170326/"

experiment = {}
for name, path in files_paths.items():
    data_in = data_import.get_data_clean(data_dir)
    # print(periods[name])
    if periods[name] is not None and periods[name] != '0':
        period = int(periods[name])
        data_in['demand'] = aux.group_patients(data_in=data_in, period_size=period)
    experiment[name] = {
        'input': data_in,
        'result': file_data[name]
        }

for name, value in experiment.items():
    print(aux.export_solution(data_directory_2, value, name))

experiment_cost = \
    {name: sum(tests.get_costs(data['result'], data['input']).values()) for name, data in experiment.items()}

experiment['201705020000']['input'].keys()
rutas = file_data['201705230608_p60_t25000_sgurobi_tight']['result']['routes_visit']
file_data['201705230608_p60_t25000_sgurobi_tight']['result']['route_job_patient']
rutas_tup = [(k[0][0], k[0][1], k[1], v) for k, v in rutas.items()]
with open('ur file.csv','w') as out:
    csv_out = csv.writer(out)
    for row in rutas_tup:
        csv_out.writerow(row)
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

# solution2 = aux.load_solution(r"C:\Users\Franco\Documents\Projects\baobab\mopta2017\results\201705070923_30_todo_gurobi_25000s.pickle")
# sum(tests.get_costs(solution2, data_in).values())

# (sol_costs.values())
# tests.check_solution(solution, data_in)
# bad_radioactive = tests.patients_radioactive(solution, data_in)
