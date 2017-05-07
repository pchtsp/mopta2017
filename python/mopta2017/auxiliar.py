import math
from collections import namedtuple
import os
import datetime
import pickle


def load_solution(path):
    if not os.path.exists(path):
        return False
    with open(path, 'rb') as f:
        return pickle.load(f)


def export_solution(path, obj):
    if not os.path.exists(path):
        return False
    path = os.path.join(path, datetime.datetime.now().strftime("%Y%m%d%H%M") + ".pickle")
    with open(path, 'wb') as f:
        pickle.dump(obj, f)
    return True


def clean_dictionary(dictionary, default_value=0):
    return {key: value for key, value in dictionary.items() if value != default_value}


def get_travel_arcs(routes_visit):
    total_clients = list(set([_tuple[1] for _tuple in routes_visit]))

    routes_client_visit = {veh_route: {client: -1 for client in total_clients} for (veh_route, _) in routes_visit}
    for (veh_route, client), values in routes_visit.items():
        routes_client_visit[veh_route][client] = values

    for route in routes_client_visit:
        routes_client_visit[route] = clean_dictionary(routes_client_visit[route], -1)

    route_clients_ordered = {route: sorted(times.keys(), key=lambda x: times[x])
                             for route, times in routes_client_visit.items()}

    route_arc = {}
    for route, clients in route_clients_ordered.items():
        client_prev = clients[0]
        route_arc[route] = []
        for client in clients[1:]:
            route_arc[route].append((client_prev, client))
            client_prev = client
        route_arc[route].append((client_prev, clients[0]))

    return route_arc


def get_radioactivity(initial_radio, time, decay):
    """
    :param initial_radio: initial radioactivity 
    :param time: time in minutes
    :param decay: % of decay every 30 minutes
    :return: radioactivity after time passes
    """
    return (decay**(time/30)) * initial_radio


def get_time_from_radio(initial_radio, end_radio, decay):
    """
    :param initial_radio: initial radioactivity 
    :param end_radio: radio level at the end 
    :param decay: % of decay every 30 minutes
    :return: time in minutes to reach that level or end_radio
    """
    return math.log(end_radio / initial_radio, decay) * 30


def limit_start_jtype_patient(data_in, min_start=False):
    """
    :param data_in: the complete data set. 
    :param min_start: boolean to know if we want to calculate the minimum start time for the job
    or the maximum start time for the job.
    :return: start time for each jtype and patient. 
    """
    job_types = list(data_in['production'].keys())
    patients = list(data_in['demand'].keys())

    # the minimum start time assumes the minimum radioactivity level and
    # the time the latest patient will be served in the group.

    # the maximum start time assumes the maximum radioactivity level and
    # the time the earliest patient will be served in the group.

    string_q = "max"
    # we decide the reference time, based on the bound:
    patient_time = {patient: data_in['demand'][patient].min for patient in patients}
    if min_start:
        string_q = "min"
        patient_time = {patient: data_in['demand'][patient].max for patient in patients}

    jtype_time = {j_type: get_time_from_radio(
        data_in['production'][j_type].radio,
        data_in['radio'][string_q],
        data_in['radio']['decay']) for j_type in job_types}

    # maximum times we round them down to constraint them further
    # minimum times we round them up to constraint them further
    start_jtype_patient = {(j_type, patient):
                               math.floor((patient_time[patient] -
                                           jtype_time[j_type] -
                                           data_in['production'][j_type].time
                                           ) / 30) * 30
                           for j_type in job_types for patient in patients
                           }
    if min_start:
        start_jtype_patient = {(j_type, patient):
                                   math.ceil((patient_time[patient] -
                                             jtype_time[j_type] -
                                              data_in['production'][j_type].time
                                              ) / 30) * 30
                               for j_type in job_types for patient in patients
                               }
    start_jtype_patient = {key: value for key, value in start_jtype_patient.items() if value > 0}
    return start_jtype_patient


def group_patients(data_in, period_size=30):
    """
    :param data_in: with 1 patient each patient
    :param period_size: minutes of grouped data.
    :return: data_in but with passengers grouped
    """
    patient = namedtuple("Patient", ['min', 'max', 'num'])
    demand = data_in['demand']
    centers = list(set([tup[0] for tup in data_in['demand']]))
    new_demand = {}
    for c in centers:
        patients_in_center = [patient for patient in demand if patient[0] == c]
        center_times = [demand[patient].max for patient in patients_in_center]
        max_time = int(max(center_times)) + period_size*2
        num_periods = int(math.ceil(max_time / period_size))
        # print(max_time)
        previous_period = 0
        patient_count = 0
        for period in list(range(num_periods))[1:]:
            period_start = period_size*previous_period
            period_end = period_size*period
            patients_in_period = [patient for patient in patients_in_center
                                  if period_end > demand[patient].min >= period_start]
            num_patients = len(patients_in_period)
            if num_patients == 0:
                continue
            patients_times = [demand[patient].min for patient in patients_in_period]
            new_min = min(patients_times)
            new_max = max(patients_times)
            new_demand[c, patient_count] = patient(new_min, new_max, num_patients)
            previous_period = period
            patient_count += 1

    new_demand = clean_dictionary(new_demand)
    return new_demand