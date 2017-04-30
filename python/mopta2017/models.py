import pulp
from mopta2017.auxiliar import limit_start_jtype_patient
import numpy as np
import sklearn.cluster as cluster
import math


def mip_model_complete(data_in, max_seconds=5000, cutoff=None):

    # TODO: change logic to match new structure of demand

    # We define the main sets:
    patients = list(data_in['demand'].keys())
    centers = list(data_in['clients'].keys())
    lines = list(range(data_in['sets']['lines']))
    job_types = list(data_in['production'].keys())
    vehicles = list(range(data_in['sets']['vehicles']))
    prod_node = 0
    # #### TEMPORAL:
    centers = [0, 1, 2, 3]
    patients = [p for p in patients if p[0] in centers if p[1] <= 20]
    vehicles = [0, 1]
    lines = [0, 1]
    num_routes_per_veh = 3
    num_jobs_slowest_line = 3
    step = 2
    # #### TEMPORAL
    # maximum parameters:
    ub = {
        'time': 24*60,  # one day
        'dosages': max(data_in['production'][j_type].dosages for j_type in job_types),
        'radio': max(data_in['production'][j_type].radio for j_type in job_types),
        'prod_time': max(data_in['production'][j_type].time for j_type in job_types)
    }

    # auxiliary sets
    # av means available

    # Job creation:
    num_jobs = sorted(range(num_jobs_slowest_line, len(lines)*step + num_jobs_slowest_line, step), reverse=True)
    # assumption: first job takes the fastest job types and the most number of jobs:
    num_jobs_line = {line: num_jobs[line] for line in lines}
    jobs = [(line, job_num) for line in lines for job_num in range(num_jobs_line[line])]
    av_job_type = [(job, j_type) for job in jobs for j_type in job_types if j_type-1 <= job[0] <= j_type]
    # av_job_type = [(job, j_type) for job in jobs for j_type in job_types]
    jobnum_per_line = {line: sorted(job[1] for job in jobs if job[0] == line) for line in lines}

    # Route creation:
    # we're assuming # routes per vehicle.
    routes = [(veh, route_num) for veh in vehicles for route_num in range(num_routes_per_veh)]
    routenum_per_veh = {veh: sorted(route[1] for route in routes if route[0] == veh) for veh in vehicles}

    arc_dist = {arc: travel.dist for arc, travel in data_in['travel'].items()}
    for center in centers:
        arc_dist[center, center] = 0
    arc_dist_array = np.array([[arc_dist[center, center2]
                                for center2 in centers if center2 != prod_node]
                               for center in centers if center != prod_node])
    half_centers = math.ceil((len(centers) - 1)/2)
    n_clusters = min(len(vehicles), int(half_centers))
    center_clusters_list = cluster.KMeans(n_clusters=n_clusters).fit(arc_dist_array).labels_
    clusters = list(set(center_clusters_list))
    center_cluster = {center: center_clusters_list[center-1] for center in centers[1:]}
    center_per_cluster = {clust: [center for center in centers[1:] if center_cluster[center] == clust]
                          for clust in clusters}
    # I will assign two clusters to each vehicle and 1 cluster to each route.
    cluster_per_veh = {veh: [c for c in clusters
                             if (int(veh) <= c <= int(veh)+1)
                             or (int(veh)+1 == len(vehicles) and c == 0)] for veh in vehicles}
    # I will assign pair routes to the first of the clusters of the vehicle
    # The other goes to odd routes
    av_route_center = [(r, c) for r in routes for clust_pos in range(len(cluster_per_veh[r[0]]))
                       for c in center_per_cluster[cluster_per_veh[r[0]][clust_pos]] if clust_pos % 2 == r[1] % 2] +\
        [(r, prod_node) for r in routes]
    av_route_centers = [(r, c1, c2) for r in routes for c1 in centers for c2 in centers
                        if (r, c1) in av_route_center if (r, c2) in av_route_center
                        if (c1 != c2 or c1 == prod_node)]
    route_center_neighbors = {route_center: [_tup[2] for _tup in av_route_centers if _tup[:2] == route_center]
                              for route_center in av_route_center}

    # TODO: MAYBE I want to constraint routes and patients. For now: I trust the centers clustering
    av_route_patient = [(r, p) for r in routes for p in patients if (r, p[0]) in av_route_center]
    av_route_patient_dic = {p: [r for r in routes if (r, p) in av_route_patient] for p in patients}

    # to tie possible routes with jobs, we're assuming that the initial routes need
    # to be only compatible with the initial jobs.
    # for example: the first 20% of routes in a given vehicle can only be compatible
    # with the first 20% of jobs done in any given line.
    # this needs to take into account when there are lines that take a lot of time to produce...

    # TODO: So far, I'm not filtering anything. we'll see.
    av_route_job = [(r, j) for j in jobs for r in routes]

    # TODO: for the jobs that start "early" and in the first lines: restrict the patients
    av_job_patient = [(j, p) for j in jobs for p in patients]
    av_job_patient_dic = {p: [j for j in jobs if (j, p) in av_job_patient] for p in patients}

    # to assign a dosage from a job to a patient via a route:
    # the job needs to be compatible with the route
    # the patient's center needs to be compatible with the route
    av_route_job_patient = []
    av_route_job_patient_dic = {p: [] for p in patients}
    for i, (route, patient) in enumerate(av_route_patient):
        for job in jobs:
            if (route, job) in av_route_job and \
                            (job, patient) in av_job_patient:
                av_route_job_patient.append((route, job, patient))
                av_route_job_patient_dic[patient].append((route, job))
        print(i)
    # av_route_job_patient = [(route, job, patient) for route, patient in av_route_patient
    #                         for job in jobs if (route, job) in av_route_job
    #                         if (job, patient) in av_job_patient]

    # based on the radioactivity of the dosage, we can calculate
    # the earliest and latest start of the job in order to arrive correctly
    # to the patient
    max_start_jtype_patient = limit_start_jtype_patient(data_in, min_start=False)
    min_start_jtype_patient = limit_start_jtype_patient(data_in, min_start=True)

    # MODEL

    model = pulp.LpProblem("mopta2017_complete", pulp.LpMinimize)

    # VARIABLES

    # Production
    line_used = pulp.LpVariable.dicts("line_used", lines, 0, 1, pulp.LpInteger)
    job_used = pulp.LpVariable.dicts("job_used", jobs, 0, 1, pulp.LpInteger)
    job_type = pulp.LpVariable.dicts("job_type", av_job_type, 0, 1, pulp.LpInteger)
    job_start_time = pulp.LpVariable.dicts("job_start_time", jobs, 0, ub['time'], pulp.LpContinuous)
    job_production = pulp.LpVariable.dicts("job_production", jobs, 0,  ub['dosages'], pulp.LpContinuous)
    # job_radio = pulp.LpVariable.dicts("job_production", jobs, 0,  ub['radio'], pulp.LpContinuous)
    job_time = pulp.LpVariable.dicts("job_time", jobs, 0, ub['prod_time'], pulp.LpContinuous)

    # Transport
    route_used = pulp.LpVariable.dicts("route_used", routes, 0, 1, pulp.LpInteger)
    vehicle_used = pulp.LpVariable.dicts("vehicle_used", vehicles, 0, 1, pulp.LpInteger)
    route_start_time = pulp.LpVariable.dicts("route_start_time", routes, 0, ub['time'], pulp.LpContinuous)
    route_end_time = pulp.LpVariable.dicts("route_end_time", routes, 0, ub['time'], pulp.LpContinuous)
    route_arrival = pulp.LpVariable.dicts("route_arrival", av_route_center, 0, ub['time'], pulp.LpContinuous)
    route_arc = pulp.LpVariable.dicts("route_arc", av_route_centers, 0, 1, pulp.LpInteger)

    # Demand:
    route_job_patient = pulp.LpVariable.dicts("route_job_patient", av_route_job_patient, 0, 1, pulp.LpInteger)
    route_job = pulp.LpVariable.dicts("route_job", av_route_job, 0, 1, pulp.LpInteger)
    job_patient = pulp.LpVariable.dicts("job_patient", av_job_patient, 0, 1, pulp.LpInteger)
    route_patient = pulp.LpVariable.dicts("route_patient", av_route_patient, 0, 1, pulp.LpInteger)

    # objective function
    # objective = pulp.LpVariable("objective", lowBound=0)

    # CONSTRAINT
    arc_time = {arc: travel.times for arc, travel in data_in['travel'].items()}
    arc_time[0, 0] = 0

    # Production
    production = data_in['production']

    # consecutive jobs in the same line:
    # first one needs to start after the previous one ends
    # the first one is used for the next one to be used
    for line in lines:
        for job_num in jobnum_per_line[line][1:]:
            model += job_start_time[line, job_num] >= job_start_time[line, job_num-1] + job_time[line, job_num-1],\
                     "sequence_jobs_in_line_{}_{}".format(line, job_num)
            model += job_used[line, job_num-1] >= job_used[line, job_num]

    # if a job is used, its line is used
    for job in jobs:
        model += line_used[job[0]] >= job_used[job], \
                 "Line_in_job_{}_{}".format(job[0], job)

    # if a job is used, it has only one type
    for job in jobs:
        model += pulp.lpSum(job_type[job, j_type]
                            for j_type in job_types if (job, j_type) in av_job_type) == job_used[job],\
                 "job_used_assign_type_{}".format(job)

    # if a job is used (this is enforced by the type constraint already).
    # it has a production equal to its type
    # it has radioactivity equal to its type
    # it has times equal to its type
    for job in jobs:
        model += job_production[job] == pulp.lpSum(job_type[job, j_type] * production[j_type].dosages
                                                   for j_type in job_types if (job, j_type) in av_job_type),\
                 "job_production_{}".format(job)
        # model += job_radio[job] <= job_used[job] * pulp.lpSum(job_type[job, j_type] * production[j_type].radio
        #                                                       for j_type in job_types)
        model += job_time[job] >= pulp.lpSum(job_type[job, j_type] * production[j_type].time
                                             for j_type in job_types if (job, j_type) in av_job_type),\
                 "job_time_{}".format(job)

    # Transport

    # route_end_time needs to be bigger the last arrival plus time to get to prod_node
    # TODO: I think this is not quite what I want... it could work though.
    for route, center in av_route_center:
        model += route_end_time[route] >= route_arrival[route, center] + arc_time[center, prod_node]

    # if a route is used, its vehicle is used
    for route in routes:
        model += vehicle_used[route[0]] >= route_used[route]

    # routes for the same vehicle can only start when the previous finishes.
    for veh in vehicles:
        for route_num in routenum_per_veh[veh][1:]:
            model += route_start_time[veh, route_num] >= route_end_time[veh, route_num-1]

    # # if a route is not used: the next route is also not used (breaks symmetry)
    # for veh in vehicles:
    #     for route_num in routenum_per_veh[veh][1:]:
    #         model += route_used[veh, route_num-1] >= route_used[veh, route_num]

    # arrival time for production node is route_start_time
    for route in routes:
        model += route_start_time[route] == route_arrival[route, prod_node]

    # for an arc to work, the arrival times need to increase (cycle cutting).
    for r, c1, c2 in av_route_centers:
        if c2 == prod_node:
            continue
        model += route_arrival[r, c2] >= arc_time[c1, c2] + route_arrival[r, c1] -\
                                         ub['time'] * (1 - route_arc[r, c1, c2])

    # max edges in and out = 1 for each route
    # we try not to force == 1 to allow to skip a center
    for route, center in av_route_center:
        model += pulp.lpSum(route_arc[route, center, neighbor]
                            for neighbor in route_center_neighbors[route, center]) == route_used[route]
        model += pulp.lpSum(route_arc[route, neighbor, center]
                            for neighbor in route_center_neighbors[route, center]) == route_used[route]

    # Demand

    # TODO: see if this can be improved...
    # the time since the production of job until the patient uses it cannot exceed a maximum
    # that depends on the type of job.
    for job, patient in av_job_patient:
        model += \
            job_start_time[job] >= pulp.lpSum(
                [min_start_jtype_patient[j_type, patient] * job_type[job, j_type]
                 for j_type in job_types if (job, j_type) in av_job_type if
                 (j_type, patient) in min_start_jtype_patient]
            ) - (1 - job_patient[job, patient]) * ub['time']

        model += \
            job_start_time[job] <= pulp.lpSum(
                [max_start_jtype_patient[j_type, patient] * job_type[job, j_type]
                 for j_type in job_types if (job, j_type) in av_job_type if
                 (j_type, patient) in max_start_jtype_patient]
            ) + (1 - job_patient[job, patient]) * ub['time']

    # TODO: this is an absurdly complicated constraint.
    # if a combo (j_type, patient) is not possible: the job cannot have both assigned.
    for j_type in job_types:
        for patient in patients:
            if (j_type, patient) not in max_start_jtype_patient:
                for job in jobs:
                    if ((job, patient) in av_job_patient and
                                (job, j_type) in av_job_type):
                        model += job_type[job, j_type] + job_patient[job, patient] <= 1,\
                        "forbiden_job_jtype_patient_{}_{}_{}".format(job, j_type, patient)

    # only a job for each patient:
    # only a route for each patient:
    for patient in patients:
        model += pulp.lpSum(job_patient[job, patient]
                            for job in av_job_patient_dic[patient]) == 1
        model += pulp.lpSum(route_patient[route, patient]
                            for route in av_route_patient_dic[patient]) == 1
        model += pulp.lpSum(route_job_patient[r, j, patient]
                            for (r, j) in av_route_job_patient_dic[patient]) == 1

    # sum of doses for a single job cannot exceed the production of the job
    for job in jobs:
        model += pulp.lpSum(job_patient[job, patient] * data_in['demand'][patient].num
                            for patient in patients if (job, patient) in av_job_patient) <= job_production[job],\
        "Limit_patients_job_{}".format(job)

    # route needs to arrive to center before patient needs dosage
    for (route, patient) in av_route_patient:
        model += \
            route_arrival[route, patient[0]] <= data_in['demand'][patient].min +\
                                                (1 - route_patient[route, patient]) * ub['time']

    # if route is not used, it cannot take passengers
    for (r, p) in av_route_patient:
        model += route_patient[r, p] <= route_used[r]

    # if a route reaches a patient, it needs to pass through the center
    for (route, patient) in av_route_patient:
        model += route_patient[route, patient] <= \
                 pulp.lpSum(route_arc[route, patient[0], c]
                            for c in centers if (route, patient[0], c) in av_route_centers)

    # route needs to start after job finishes, if assigned.
    for (route, job) in av_route_job:
        model += route_start_time[route] >= job_start_time[job] + job_time[job] - \
                                            (1 - route_job[route, job]) * ub['time']

    # all three need to be assigned in order for the main variable to make sense
    for (route, job, patient) in av_route_job_patient:
        model += route_job_patient[route, job, patient] <= route_job[route, job]
        model += route_job_patient[route, job, patient] <= route_patient[route, patient]
        model += route_job_patient[route, job, patient] <= job_patient[job, patient]

    # OBJECTIVE FUNCTION
    costs = data_in['costs']
    cost_prod_fixed = costs['production']['fixed']
    cost_prod_var = costs['production']['variable']

    model += pulp.lpSum([line_used[line] * cost_prod_fixed for line in lines] +
                        [job_type[job, j_type] * data_in['production'][j_type].time * cost_prod_var
                         for job, j_type in av_job_type] +
                        [route_arc[r, c1, c2] * data_in['travel_costs'][c1, c2] for r, c1, c2 in av_route_centers] +
                        [vehicle_used[veh] * costs['route']['fixed'] for veh in vehicles]
                        )
    # if cutoff is not None:
    #     model += objective <= cutoff
    # model += objective

    # SOLVING

    model.solve(pulp.PULP_CBC_CMD(maxSeconds=max_seconds, msg=1, fracGap=0))

    # FORMAT SOLUTION
    _jobs_used = [job for job in jobs if job_used[job].value()]
    _job_start_time = {job: job_start_time[job].value() for job in _jobs_used}
    _job_finish_time = {job: _job_start_time[job] + job_time[job].value() for job in _jobs_used}
    _job_type = {job: j_type for job, j_type in av_job_type if job_type[job, j_type].value() if job in _jobs_used}

    _routes_used = [route for route in routes if route_used[route].value()]
    _route_start_time = {route: route_start_time[route].value() for route in _routes_used}
    _route_arrival = {(route, center): route_arrival[route, center].value()
                      for (route, center) in av_route_center if route in _routes_used}
    _route_job_patient = [(r, j, p) for r, j, p in av_route_job_patient if route_job_patient[(r, j, p)].value()]
    _route_arcs = [_tup for _tup in av_route_centers if route_arc[_tup].value()]
    solution = {
        'jobs_start': _job_start_time,
        'jobs_type': _job_type,
        'routes_start': _route_start_time,
        'routes_visit': _route_arrival,
        'route_job_patient': _route_job_patient,
    }
    return solution
