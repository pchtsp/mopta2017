import mopta2017.input_data as data_import
import mopta2017.auxiliar as aux
import mopta2017.models as models

data_dir = "../data/20170326/"
data_in = data_import.get_data_clean(data_dir)

# Optionally, we group patients according to their proximity
data_in['demand'] = aux.group_patients(data_in=data_in, period_size=60)

###TEMPORAL
# data_in['clients'] = {cl: name for cl, name in data_in['clients'].items() if cl in range(8)}
# data_in['demand'] = {p: data for p, data in data_in['demand'].items() if p[0] in data_in['clients'].keys()}
# data_in['sets']['vehicles'] = 4
data_in['sets']['lines'] = 2
# data_in['production'] = data_in['production']
###TEMPORAL

# Configuration
data_in['sets']['num_routes_per_veh'] = 2  # 4
data_in['sets']['num_jobs_slowest_line'] = 6  # 3
data_in['sets']['step'] = 2
path = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results'

# solution2 = aux.load_solution(r"C:\Users\Franco\Documents\Projects\baobab\mopta2017\results\201705070923_30min_25000s.pickle")
solution = models.mip_model_complete(data_in=data_in, max_seconds=3000)
aux.export_solution(path, solution)