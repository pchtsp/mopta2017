from mopta2017.auxiliar import get_travel_arcs, get_radioactivity


def patients_not_covered(solution, data_in):
    # we check if patients are being covered
    patients = data_in['demand'].keys()
    patients_covered = [tup[2] for tup in solution['route_job_patient']]
    patients_not_covered = [patient for patient in patients if patient not in patients_covered]

    return patients_not_covered


def patients_radioactive(solution, data_in):
    # we check if patients receive the correct radioactive level
    # we need to calculate the jobs_end based on the duration of the job
    time_to_first_patient = {(job, patient): data_in['demand'][patient]['min'] -
                                             solution['jobs_start'][job] -
                                             data_in['production'][solution['jobs_type'][job]]['time']
                             for (_, job, patient) in solution['route_job_patient']}

    time_to_last_patient = {(job, patient): data_in['demand'][patient]['max'] -
                                            solution['jobs_start'][job] -
                                            data_in['production'][solution['jobs_type'][job]]['time']
                            for (_, job, patient) in solution['route_job_patient']}

    initial_radio_in_job = {job: data_in['production'][job_type]['radio']
                                  for job, job_type in solution['jobs_type'].items()}

    radioactive_in_first_patient = \
        {patient: get_radioactivity(initial_radio_in_job[job],
                                    time_to_first_patient[job, patient],
                                    data_in['radio']['decay'])
         for (_, job, patient) in solution['route_job_patient']}

    radioactive_in_last_patient = \
        {patient: get_radioactivity(initial_radio_in_job[job],
                                    time_to_last_patient[job, patient],
                                    data_in['radio']['decay'])
         for (_, job, patient) in solution['route_job_patient']}

    patients_bad_radioactive = \
        {patient: (radioactive_in_first_patient[patient], radioactive_in_last_patient[patient])
         for (_, _, patient) in solution['route_job_patient']
         if not (radioactive_in_first_patient[patient] <= data_in['radio']['max'] and
                 radioactive_in_last_patient[patient] >= data_in['radio']['min'])}
    return patients_bad_radioactive


def get_job_capacity(solution, data_in, all_jobs=False):

    job_demand = {job: 0 for job in solution['jobs_start']}
    for (_, job, p) in solution['route_job_patient']:
        job_demand[job] += data_in['demand'][p].num
    # job_demand = clean_dictionary(job_demand)
    job_idle_capacity = {job: data_in['production'][solution['jobs_type'][job]]['dosages'] - job_demand[job]
                         for job in job_demand}
    if not all_jobs:
        job_idle_capacity = {job: cap for job, cap in job_idle_capacity.items() if cap < 0}

    return job_idle_capacity


def get_overlapping_jobs_in_line(solution, data_in):
    jobs_start = solution['jobs_start']
    jobs = [job for job in solution['jobs_start']]
    jobs_end = {job: jobs_start[job] + data_in['production'][solution['jobs_type'][job]]['time']
                for job in jobs}
    lines = list(set([job[0] for job in jobs]))
    jobs_per_line = {line: [job for job in jobs if job[0] == line] for line in lines}

    cliques = [(job1, job2) for line in lines for job1 in jobs_per_line[line]
                        for job2 in jobs_per_line[line] if job1[1] != job2[1]
                        ]

    overlapping_jobs = [(job1, job2) for (job1, job2) in cliques
                        if jobs_start[job2] >= jobs_start[job1] >= jobs_end[job2]]

    return overlapping_jobs


def get_overlapping_routes_in_veh(solution, data_in):
    routes = list(solution['routes_start'].keys())
    vehicles = list(set([route[0] for route in routes]))
    route_start = solution['routes_start']
    route_end_info = {route: max([visit for visit in solution['routes_visit'].items()
                                  if visit[0][0] == route], key=lambda key: key[1])
                      for route in routes}
    route_last_visit_time = {route: route_end_info[route][1] for route in routes}
    route_last_visit_node = {route: route_end_info[route][0][1] for route in routes}

    #  if route_last_visit_node[route], the route was not used
    route_end = {route: route_last_visit_time[route] + data_in['travel'][route_last_visit_node[route], 0]['times']
                 for route in routes if route_last_visit_node[route] != 0}

    routes_per_veh = {veh: [route for route in routes if route[0] == veh if route_last_visit_node[route] != 0]
                      for veh in vehicles }

    cliques = [(route, route2) for veh in vehicles for route in routes_per_veh[veh]
               for route2 in routes_per_veh[veh] if route[1] != route2[1]
               ]

    overlapping = [(route, route2) for (route, route2) in cliques
                  if route_start[route2] >= route_start[route] >= route_end[route2]]

    return overlapping


def get_routes_before_job(solution, data_in):
    route_job = [(tup[0], tup[1]) for tup in solution['route_job_patient']]
    jobs_start = solution['jobs_start']
    jobs = [job for job in solution['jobs_start']]
    jobs_end = {job: jobs_start[job] + data_in['production'][solution['jobs_type'][job]]['time']
                for job in jobs}

    route_before_job = [(r, j) for (r, j) in route_job if solution['routes_start'][r] < jobs_end[j]]
    return route_before_job


def get_costs(solution, data_in):
    costs = data_in['costs']
    route_arcs = get_travel_arcs(solution['routes_visit'])

    travel_var_cost = sum(data_in['travel_costs'][arc] for route in route_arcs for arc in route_arcs[route])

    vehicle_used = set(_tup[0][0] for _tup in solution['route_job_patient'])
    vehicle_cost = len(vehicle_used) * costs['route']['fixed']

    lines_used = set([tup[0] for tup in solution['jobs_start']])
    lines_time_used = sum(data_in['production'][solution['jobs_type'][tup]]['time'] for tup in solution['jobs_type'])

    production_fix_cost = len(lines_used) * costs['production']['fixed']
    production_var_cost = lines_time_used * costs['production']['variable']

    return {
        'travel_var': travel_var_cost,
        'travel_fix': vehicle_cost,
        'prod_fix': production_fix_cost,
        'prod_var': production_var_cost
    }


def check_solution(solution, data_in):
    """
    :param solution: routes, jobs and job-route-patient assignment.
    :param data_in: the initial data set
    :return: returns 1 if it's feasible, 0 if not
    Also, it prints the infeasible things it finds.
    """
    solution_ok = 1
    not_covered = patients_not_covered(solution, data_in)
    num_patients_not_covered = len(not_covered)

    if num_patients_not_covered > 0:
        print('There are {} patients without treatment'.format(num_patients_not_covered))
        solution_ok = 0

    patients_bad_radioactive = patients_radioactive(solution, data_in)
    num_patients_bad_radioactive = len(patients_bad_radioactive)
    if num_patients_bad_radioactive > 0:
        print('There are {} patients with bad radioactive component'.format(num_patients_bad_radioactive))
        solution_ok = 0

    idle_capacity = get_job_capacity(solution, data_in)
    num_jobs_over_capacity = len(idle_capacity)
    if num_jobs_over_capacity > 0:
        print('There are {} jobs with over capacity'.format(num_jobs_over_capacity))
        solution_ok = 0

    overlapping = get_overlapping_jobs_in_line(solution, data_in)
    num_jobs_overlapping = len(overlapping)
    if num_jobs_overlapping > 0:
        print("There are {} jobs overlapping in the same line".format(num_jobs_overlapping))
        solution_ok = 0

    overlapping = get_overlapping_routes_in_veh(solution, data_in)
    num_routes_overlapping = len(overlapping)
    if num_routes_overlapping > 0:
        print("There are {} routes ovelapping in the same vehicle".format(num_routes_overlapping))
        solution_ok = 0

    return solution_ok
