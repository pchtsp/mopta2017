from mopta2017.auxiliar import get_travel_arcs


def patients_not_covered(solution, data_in):
    # we check if patients are being covered
    patients = data_in['demand'].keys()
    patients_covered = [tup[2] for tup in solution['route_job_patient']]
    patients_not_covered = [patient for patient in patients if patient not in patients_covered]

    return patients_not_covered


def patients_radioactive(solution, data_in):
    # we check if patients receive the correct radioactive level
    time_to_patient = {(job, patient): data_in['demand'][patient] - solution['jobs_start'][job]
                       for (_, job, patient) in solution['route_job_patient']}

    initial_radioactive_in_job = {job: data_in['production'][solution['jobs_type'][job]].a
                                  for job in solution['jobs_start']}

    radioactive_in_patient = \
        {patient: initial_radioactive_in_job[job]*(data_in['radio']['decay']**int(time_to_patient[job, patient]/30))
         for (_, job, patient) in solution['route_job_patient']}

    patients_bad_radioactive = \
        {patient: radioactive_in_patient[patient] for (_, _, patient) in solution['route_job_patient']
         if not (data_in['radio']['min'] <= radioactive_in_patient[patient] <= data_in['radio']['max'])}
    return patients_bad_radioactive


def get_job_capacity(solution, data_in):

    job_demand = {job: 0 for job in solution['jobs_start']}
    for (_, job, _) in solution['route_job_patient']:
        job_demand[job] += 1
    # job_demand = clean_dictionary(job_demand)
    job_idle_capacity = {job: data_in['production'][solution['jobs_type'][job]].b - job_demand[job]
                         for job in job_demand}
    return job_idle_capacity


def get_costs(solution, data_in):
    costs = data_in['costs']
    route_arcs = get_travel_arcs(solution['routes_visit'])

    travel_time_cost = sum(data_in['travel'][arc].times * costs['route']['hour']
                           for route in route_arcs for arc in route_arcs[route])
    travel_dist_cost = sum(data_in['travel'][arc].dist * costs['route']['kilometer']
                           for route in route_arcs for arc in route_arcs[route])

    lines_used = set([tup[0] for tup in solution['jobs_start']])
    lines_time_used = sum(data_in['production'][solution['jobs_type'][tup]].p for tup in solution['jobs_type'])

    production_fix_cost = len(lines_used) * costs['production']['fixed']
    production_var_cost = lines_time_used * costs['production']['variable']

    return {
        'travel_time': travel_time_cost,
        'travel_dist': travel_dist_cost,
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

    return solution_ok