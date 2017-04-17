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
    time_to_patient = {(job, patient): data_in['demand'][patient] -
                                       solution['jobs_start'][job] -
                                       data_in['production'][solution['jobs_type'][job]].time
                       for (_, job, patient) in solution['route_job_patient']}

    initial_radio_in_job = {job: data_in['production'][job_type].radio
                                  for job, job_type in solution['jobs_type'].items()}

    radioactive_in_patient = \
        {patient: get_radioactivity(initial_radio_in_job[job], time_to_patient[job, patient], data_in['radio']['decay'])
         for (_, job, patient) in solution['route_job_patient']}

    patients_bad_radioactive = \
        {patient: radioactive_in_patient[patient] for (_, _, patient) in solution['route_job_patient']
         if not (data_in['radio']['min'] <= radioactive_in_patient[patient] <= data_in['radio']['max'])}
    return patients_bad_radioactive


def get_job_capacity(solution, data_in, all_jobs=False):

    job_demand = {job: 0 for job in solution['jobs_start']}
    for (_, job, _) in solution['route_job_patient']:
        job_demand[job] += 1
    # job_demand = clean_dictionary(job_demand)
    job_idle_capacity = {job: data_in['production'][solution['jobs_type'][job]].dosages - job_demand[job]
                         for job in job_demand}
    if not all_jobs:
        job_idle_capacity = {job: cap for job, cap in job_idle_capacity.items() if cap < 0}

    return job_idle_capacity


def get_overlapping_jobs_in_line(solution, data_in):
    jobs_start = solution['jobs_start']
    jobs = [job for job in solution['jobs_start']]
    jobs_end = {job: jobs_start[job] + data_in['production'][solution['jobs_type'][job]].time
                for job in jobs}
    lines = list(set([job[0] for job in jobs]))
    jobs_per_line = {line: [job for job in jobs if job[0] == line] for line in lines}

    cliques = [(job1, job2) for line in lines for job1 in jobs_per_line[line]
                        for job2 in jobs_per_line[line] if job1[1] != job2[1]
                        ]

    overlapping_jobs = [(job1, job2) for (job1, job2) in cliques
                        if jobs_start[job2] >= jobs_start[job1] >=  jobs_end[job2]]

    return overlapping_jobs


def get_routes_before_job(solution, data_in):
    route_job = [(tup[0], tup[1]) for tup in solution['route_job_patient']]
    jobs_start = solution['jobs_start']
    jobs = [job for job in solution['jobs_start']]
    jobs_end = {job: jobs_start[job] + data_in['production'][solution['jobs_type'][job]].time
                for job in jobs}

    route_before_job = [(r, j) for (r, j) in route_job if solution['routes_start'][r] < jobs_end[j]]
    return route_before_job


def get_costs(solution, data_in):
    costs = data_in['costs']
    route_arcs = get_travel_arcs(solution['routes_visit'])

    travel_time_cost = sum(data_in['travel'][arc].times * costs['route']['minute']
                           for route in route_arcs for arc in route_arcs[route])
    travel_dist_cost = sum(data_in['travel'][arc].dist * costs['route']['kilometer']
                           for route in route_arcs for arc in route_arcs[route])

    vehicle_used = set(_tup[0][0] for _tup in solution['route_job_patient'])
    vehicle_cost = len(vehicle_used) * costs['route']['fixed']

    lines_used = set([tup[0] for tup in solution['jobs_start']])
    lines_time_used = sum(data_in['production'][solution['jobs_type'][tup]].time for tup in solution['jobs_type'])

    production_fix_cost = len(lines_used) * costs['production']['fixed']
    production_var_cost = lines_time_used * costs['production']['variable']

    return {
        'travel_time': travel_time_cost,
        'travel_dist': travel_dist_cost,
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

    return solution_ok
