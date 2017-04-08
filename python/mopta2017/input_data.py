import os
import re
from collections import namedtuple


travel = namedtuple("Travel", ['times', 'dist'])
line = namedtuple("Line", ['p', 'b', 'a'])

def get_data_clean(data_directory):

    file_data = get_main_data(data_directory)

    params = {x: file_data[x] for x in file_data.keys() if x not in
              ['J', 'L_ij', 'production_line_parameters', 'S_j', 'T_ij', 't']}

    params['production'] = format_production_params(file_data['production_line_parameters'])
    params['demand'] = format_appointments_time(file_data['t'])
    params['travel'] = format_travel_times_distances(file_data['T_ij'], file_data['L_ij'])
    params['clients'] = format_clients_data(file_data['J'])

    # we will add unloading times to the transport time depending on the destination:
    # it doesn't make sense to have unloading times in the production node.
    unloading_times = format_waiting_params(file_data['S_j'])
    unloading_times[0] = 0
    for (i, j) in params['travel']:
        new_time = params['travel'][(i, j)].times + unloading_times[j]
        params['travel'][(i, j)] = \
            travel(new_time, params['travel'][(i, j)].dist)

    return params


def get_main_data(data_directory):
    files_list = os.listdir(data_directory)
    files_names = [os.path.splitext(name)[0] for name in files_list]
    files_paths = [data_directory + file for file in files_list]

    _file_data = {}
    for file, path in enumerate(files_paths):
        with open(path, 'r') as f:
            _file_data[files_names[file]] = [re.split("\s+", y) for y in [x for x in f.read().split("\n") if x != '']]

    # here we delete empty elements and empty lists
    for file in _file_data:
        for j, x in enumerate(_file_data[file]):
            _file_data[file][j] = [y for y in x if y != '']
        _file_data[file] = [x for x in _file_data[file] if len(x) > 0]

    # here we extract one dimensional values:
    for file in _file_data:
        for j, x in enumerate(_file_data[file]):
            if len(x) == 1:
                _file_data[file][j] = x[0]
        if len(_file_data[file]) == 1:
            _file_data[file] = _file_data[file][0]

    # here we convert all one dimensional values into floats:
    for file in _file_data:
        if type(_file_data[file]) is not list:
            _file_data[file] = float(_file_data[file])
        
    return _file_data


def format_production_params(production_params):
    dict_out = {}
    for i, row in enumerate(production_params):
        col1 = re.search('^\d+', (row[0]))
        if col1 is not None:
            # this avoids getting the first row or getting an runtime error
            # because of the regex syntax going wrong.
            col1 = float(col1.group())
            dict_out[i] = line(col1, float(row[1]), float(row[2]))
    return dict_out


def format_waiting_params(data):
    dict_out = {}
    for i, row in enumerate(data):
        if i > 0:
            dict_out[int(row[0])] = float(row[1])
    return dict_out


def format_travel_times_distances(times, distances):
    dict_out_times = {}
    for i, row in enumerate(times):
        if i == 0:
            continue
        col2 = re.search('^\d+', row[2])
        col3 = re.search('^\d+', row[3])
        if col2 is not None and col3 is not None:
            time = float(col2.group())*60 + float(col3.group())
            dict_out_times[(int(row[0]), int(row[1]))] = time

    dict_out_dist = {}
    for i, row in enumerate(distances):
        if i == 0:
            continue
        dict_out_dist[(int(row[0]), int(row[1]))] = float(row[2])

    dict_out = {}
    # I put both values in the same tuple.
    # I also make the matrix symmetric
    for _tuple in dict_out_times.keys():
        dict_out[_tuple] = travel(dict_out_times[_tuple], dict_out_dist[_tuple])
        dict_out[(_tuple[1], _tuple[0])] = travel(dict_out_times[_tuple], dict_out_dist[_tuple])

    return dict_out


def format_appointments_time(times):
    """
    :param times: sequence of time of the day for each client.
    :return: dictionary of minute on the day indexed by client and correlative number.
    """
    dict_out = {}
    for i, row in enumerate(times):
        if i == 0:
            continue
        for j, row2 in enumerate(row):
            if j == 0:
                continue
            hour = re.search('^\d+:?', row2).group()[:-1]
            minute = re.search(':?\d+$', row2).group()[1:]
            if row2 == '':
                time = 0
            else:
                time = float(hour)*60 + float(minute)
            dict_out[(int(row[0]), j)] = time

    return dict_out


def format_clients_data(data):
    dict_out = {}
    for i, row in enumerate(data):
        dict_out[int(row[0])] = " ".join([row[1], row[2]])
    return dict_out

if __name__ == "__main__":
    data_dir = "../data/"
    data_out = get_data_clean(data_dir)
