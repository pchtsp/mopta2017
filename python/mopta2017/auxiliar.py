import math


def clean_dictionary(dictionary, default_value=0):
    return {key: value for key, value in dictionary.items() if value != default_value}


def get_travel_arcs(routes_visit):
    total_clients = list(set([_tuple[2] for _tuple in routes_visit]))

    routes_client_visit = {(veh, route): {client: -1 for client in total_clients} for (veh, route, _) in routes_visit}
    for (veh, route, client), values in routes_visit.items():
        routes_client_visit[(veh, route)][client] = values

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
    return (decay**int(math.ceil(time/30))) * initial_radio


def get_time_from_radio(initial_radio, end_radio, decay):
    """
    :param initial_radio: initial radioactivity 
    :param end_radio: radio level at the end 
    :param decay: % of decay every 30 minutes
    :return: time in minutes to reach that level or end_radio
    """
    return round(math.log(end_radio / initial_radio, decay) * 30)


def limit_start_jtype_patient(data_in, min_start=False):
    job_types = list(data_in['production'].keys())
    patients = list(data_in['demand'].keys())

    string_q = "min"
    if not min_start: string_q = "max"

    jtype_time = {j_type: get_time_from_radio(
        data_in['production'][j_type].radio,
        data_in['radio'][string_q],
        data_in['radio']['decay']) for j_type in job_types}

    start_jtype_patient = {(j_type, patient):
                                data_in['demand'][patient] -
                                (jtype_time[j_type] +
                                 data_in['production'][j_type].time)
                                 for j_type in job_types for patient in patients
                                 }
    start_jtype_patient = {key: value for key, value in start_jtype_patient.items() if value>0}
    return start_jtype_patient
