import pulp


def mip_model_complete(data_in, max_seconds):

    # We define the main sets:
    patients = list(data_in['demand'].keys())
    centers = list(data_in['clients'].keys())
    lines = list(range(data_in['sets']['lines']))
    job_types = list(data_in['production'].keys())
    vehicles = list(range(data_in['sets']['vehicles']))

    # auxiliary sets
    # av means available
    # Job creation:
    num_jobs_slowest_line = 6
    step = 2
    num_jobs = sorted(range(num_jobs_slowest_line, len(lines)*step + num_jobs_slowest_line, step), reverse=True)
    # assumption: first job takes the fastest job types and the most number of jobs:
    jobs = [(line, job_num) for line in lines for job_num in range(num_jobs[line])]
    av_job_type = [(job, j_type) for job in jobs for j_type in job_types if j_type-1 <= job[0] <= j_type]

    # Route creation:
    # we're assuming 8 routes per vehicle.
    num_routes_per_veh = 8
    routes = [(veh, route_num) for veh in vehicles for route_num in range(num_routes_per_veh)]
    # TODO: this implies doing some clustering.
    av_route_center = [(r, c) for r in routes for c in centers]
    av_route_centers = [(r, c1, c2) for r in routes for c1 in centers for c2 in centers]
    av_route_patient = []  # this makes sense? could use same logic than jobs and routes...
    # to tie possible routes with jobs, we're assuming that the initial routes need
    # to be only compatible with the initial jobs.
    # for example: the first 20% of routes in a given vehicle can only be compatible
    # with the first 20% of jobs done in any given line.
    # this needs to take into account there are lines that take a lot of time to produce...
    # TODO: criteria for job_routes.
    av_job_route = [(j, r) for j in jobs for r in routes]

    # to assign a dosage from a job to a patient via a route:
    # the job needs to be compatible with the route
    # the patient's center needs to be compatible with the route
    av_route_job_patient = [(route, job, patient) for job, route in av_job_route
                            for patient in patients if (route, patient[0]) in av_route_center]

    # TODO: will I restrict this??
    av_job_patient = [(j, p) for j in jobs for p in patients]
    # MODEL

    model = pulp.LpProblem("mopta2017_complete", pulp.LpMinimize)

    # VARIABLES

    # Production
    line_used = pulp.LpVariable.dicts("line_used", lines, 0, 1, pulp.LpInteger)
    job_used = pulp.LpVariable.dicts("job_used", jobs, 0, 1, pulp.LpInteger)
    job_type = pulp.LpVariable.dicts("job_type", av_job_type, 0, 1, pulp.LpInteger)
    job_start_time = pulp.LpVariable.dicts("job_start_time", jobs, 0, 24*60, pulp.LpContinuous)

    # Transport
    route_used = pulp.LpVariable.dicts("route_used", routes, 0, 1, pulp.LpInteger)
    route_start_time = pulp.LpVariable.dicts("route_start_time", routes, 0, 24*60, pulp.LpContinuous)
    route_arrival = pulp.LpVariable.dicts("route_arrival", av_route_center, 0, 24*60, pulp.LpContinuous)
    route_arc = pulp.LpVariable.dicts("route_arc", av_route_centers, 0, 1, pulp.LpInteger)

    # Demand:
    route_job_patient = pulp.LpVariable.dicts("route_job_patient", av_route_job_patient , 0, 1, pulp.LpInteger)
    job_patient = pulp.LpVariable.dicts("job_patient", av_job_patient, 0, 1, pulp.LpInteger)
    route_patient = pulp.LpVariable.dicts("route_patient", av_route_patient, 0, 1, pulp.LpInteger)

    # CONSTRAINTS

    # Production
    # if a job is used, its line is used
    for job in jobs:
        model += line_used[job[0]] >= job_used[job]

    # if a job is used, it has only one type
    for job in jobs:
        model += pulp.lpSum(job_type[job, type]
                            for j_type in job_types if (job, j_type) in av_job_type) ==  job_used[job]

    # TODO: if a job is used, it has a production equal to its type

    # Transport
    # initial node of route is 0
    # end node of route is 0
    # for an arc to work, the arrival times needs to increase (loop cutting).
    # routes for the same vehicle can only start when the previous finishes.

    # Main variable
    # route needs to start after job finishes.
    # route needs to arrive to center before patient needs dosage
    # sum of doses for a single job cannot exceed the production of the job
    # the time since the production of job until the patient uses it cannot exceed a maximum
        # that depends on the type of job

    # OBJECTIVE FUNCTION
    cost_prod_fixed = data_in['costs']['production']['fixed']
    cost_prod_var = data_in['costs']['production']['variable']

    cost_arc = {(c1, c2): data_in['travel'][c1, c2].dist * data_in['costs']['route']['kilometer'] +
                data_in['travel'][c1, c2].times * data_in['costs']['route']['minute']
                for c1, c2 in data_in['travel']}

    model += pulp.lpSum([line_used[line] * cost_prod_fixed for line in lines] +
                        [job_type[job, j_type] * data_in['production'][j_type].time * cost_prod_var
                         for job, j_type in av_job_type] +
                        [route_arc[r, c1, c2]*cost_arc[c1, c2] for r, c1, c2 in av_route_centers]
                        )
    # SOLVING

    # model.solve(GLPK_CMD())
    model.solve(pulp.PULP_CBC_CMD(maxSeconds=max_seconds, msg=1))

    # FORMAT SOLUTION
    _jobs_used = [job for job in jobs if pulp.value(job_used[job])]
    _job_start_time = {job: pulp.value(job_start_time[job]) for job in _jobs_used}
    _job_type = {job: j_type for job, j_type in av_job_type if pulp.value(job_type[job, j_type]) if job in _jobs_used}

    _routes_used = [route for route in routes if pulp.value(route_used[route])]
    _route_start_time = {route: pulp.value(route_start_time) for route in _routes_used}
    _route_arrival = {(route, center): pulp.value(route_arrival[route])
                      for route, center in av_route_center if route in _routes_used}
    _route_job_patient = [(r, j, p) for r, j, p in av_route_job_patient if pulp.value(route_job_patient)]
    solution = {
        'jobs_start': _job_start_time
        , 'jobs_type': _job_type
        , 'routes_start': _route_start_time
        , 'routes_visit': _route_arrival
        , 'route_job_patient': _route_job_patient
    }
    return solution
