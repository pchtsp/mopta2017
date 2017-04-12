from mopta2017.auxiliar import clean_dictionary

# from collections import namedtuple
# job_tuple = namedtuple("Job", ['start', 'type'])


def initial_solution(data_in):

    # let's make every production line to produce something in parallel.
    start_time = 0  # start of day
    end_time = 24*60  # end of day
    horizon_size = end_time - start_time

    # ##################
    # ##PRODUCTION######
    # ##################
    # each line has to have a maximum number of jobs in horizon
    lines = range(1, int(data_in['sets']['lines']+1))

    # TODO: change this to a better assumption
    # we're assuming that each job in the same line has the same "type".
    # the type should go to the job, not the line...
    line_type = {line: line for line in lines}
    job_types_available = data_in['production']

    line_durations = {l: job_types_available[line_type[l]].p for l in lines}
    max_jobs = {l: int(horizon_size / line_durations[line_type[l]]) for l in lines}

    # now we start creating the "job" variables.

    job_start_times_list = \
        {l:
         [job * time for job, time in zip(range(max_jobs[l]), max_jobs[l] * [line_durations[l]])]
         for l in line_durations
         }
    job_end_times_list = {l: [time + line_durations[l] for time in job_start_times_list[l]] for l in lines}

    # we get start times and end times with an additional job index (tuple line-job).
    job_start_times = {}
    job_end_times = {}
    for line in job_start_times_list:
        for job, value in enumerate(job_start_times_list[line]):
            job_start_times[line, job] = job_start_times_list[line][job]
            job_end_times[line, job] = job_end_times_list[line][job]

    job_type = {job: line_type[job[0]] for job in job_start_times}
    job_production = {job: job_types_available[job_type[job]].b for job in job_start_times}
    job_initial_radio = {job: job_types_available[job_type[job]].a for job in job_start_times}

    #  ##################
    #  ##TRANSPORT#######
    #  ##################

    # trivial solution: each vehicle to one center.
    vehicles = range(int(data_in['sets']['vehicles']))
    arcs = data_in['travel'].keys()
    times_prod_to_center = {center: data_in['travel'][node1, center].times for node1, center in arcs if node1 == 0}
    times_center_to_prod = {center: data_in['travel'][center, node1].times for node1, center in arcs if node1 == 0}
    vehicle_to_center = {veh: veh+1 for veh in vehicles}
    duration_trip = {veh: times_prod_to_center[vehicle_to_center[veh]] + times_center_to_prod[vehicle_to_center[veh]]
                     for veh in vehicles}
    max_trips = {veh: int(horizon_size / duration_trip[veh]) for veh in vehicles}
    route_start_times = \
        {(veh, route): route * duration_trip[veh] for veh in vehicles for route in range(max_trips[veh])}
    routes = route_start_times.keys()
    # route_end_times = \
    #     {veh_route: route_start_times[veh_route] + duration_trip[veh_route[0]] for veh_route in routes}

    # arrivals are times when each route passes through each node in its path. Since the first node has no
    # vehicle (or route) assigned, we need to assume the starting time of the route is the arrival to the node0
    route_arrivals = \
        {(veh_route[0], veh_route[1], vehicle_to_center[veh_route[0]]):
             route_start_times[veh_route] + times_prod_to_center[vehicle_to_center[veh_route[0]]]
         for veh_route in routes}
    route_arrivals_node0 = \
        {(veh_route[0], veh_route[1], 0):
             route_start_times[veh_route]for veh_route in routes}
    route_arrivals.update(route_arrivals_node0)

    # Now that we have the routes, we can decided how much each route needs.
    # basically: all the consumption between consecutive routes.
    center_demand = data_in['demand']
    centers = data_in['clients'].keys()
    center_num_clients = {center: 0 for center in centers}
    for (center, pos) in center_demand:
        center_num_clients[center]+=1

    # I prepare an ordered list of routes per center:
    veh_routes_per_center = {}
    for center in centers:
        veh_routes_per_center[center] = [(veh, route) for (veh, route) in routes
                                         if (veh, route, center) in route_arrivals]
        veh_routes_per_center[center].sort(key=lambda x: route_arrivals[x[0], x[1], center])

    #  ##################
    #  ##TRANSPORT/DEMAND
    #  ##################

    # I fill the routes with the number of doses they need
    # I also match patients with routes.
    route_needs = {route: 0 for route in routes}
    route_patient = {(route, patient): 0 for route in routes for patient in center_demand}
    for center in centers:
        if len(veh_routes_per_center[center]) == 0:
            continue
        arrive_time = -1
        for route in veh_routes_per_center[center]:
            arrive_time_next_route = route_arrivals[route[0], route[1], center]
            for pos in range(1, center_num_clients[center]):
                if arrive_time <= center_demand[(center, pos)] < arrive_time_next_route:
                    route_patient[(route, (center, pos))] = 1
                    route_needs[route] += 1
            arrive_time = arrive_time_next_route
    route_needs = clean_dictionary(route_needs)
    route_patient = clean_dictionary(route_patient)
    # TODO: routes for the last hospital AND for some other clients that I haven't found

    #  ##################
    #  #TRANSPORT/PRODUCE
    #  ##################

    # Now we tie transport with production... so that:
    # everything that is being produced gets into the vehicle as soon as possible.
    # but only until the vehicle is full with all the needed doses.
    # this means that I need to calculate the jobs that finished since the last trip
    # this is similar to the demand math but with

    # route_available = {route: 0 for route in route_needs}
    # routes_ordered = sorted(list(route_needs.keys()), key=lambda x: route_start_times[x])
    jobs_ordered = sorted(list(job_start_times.keys()), key=lambda x: job_start_times[x])
    route_job_patient = {(route, job, patient): 0 for (route, patient) in route_patient for job in job_start_times}

    # in order to match production to routes to patients we need to:
    # 1. be sure the quality of the radioactive material is still good.
    # 2. be sure not to surpass the maximum production allowed.
    # keep track of what is being produced and stored.
    # 3. be sure to assign only production that ends before the route starts
    # 4. patient is not satisfied by any route.

    job_remain_production = {job: job_production[job] for job in job_start_times}
    route_patient_satisfied = {key: 0 for key in route_patient}
    max_radio = data_in['radio']['max']
    min_radio = data_in['radio']['min']
    ratio_radio = data_in['radio']['decay']

    for job in jobs_ordered:
        for route, patient in route_patient:
            # we do some math to check the radioactive decay
            periods = int((center_demand[patient] - job_end_times[job])/30)
            radio_patient = job_initial_radio[job]*(ratio_radio**periods)

            # we do some checks to see if it makes sense to make the assignment:
            if not (min_radio <= radio_patient <= max_radio) or \
                job_remain_production[job] == 0 or \
                route_start_times[route] <= job_end_times[job] or \
                route_patient_satisfied[route, patient] != 0:
                continue

            # if this is a good candidate, then assign jobs, routes and patients:
            job_remain_production[job] -= 1
            route_patient_satisfied[route, patient] = 1
            route_job_patient[route, job, patient] = 1

    route_job_patient = clean_dictionary(route_job_patient)

    # I only need to register the jobs that actually serve a patient:
    jobs_assigned = set([tup[2] for tup in route_job_patient])
    job_start_times = {job: time for job, time in job_start_times.items() if job in jobs_assigned}
    job_type = {job: j_type for job, j_type in job_type.items() if job in jobs_assigned}
    solution = {
        'jobs_start': job_start_times
        , 'jobs_type': job_type
        , 'routes_start': route_start_times
        , 'routes_visit': route_arrivals
        , 'route_job_patient': route_job_patient
    }
    return solution