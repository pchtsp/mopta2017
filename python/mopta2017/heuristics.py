from mopta2017.auxiliar import clean_dictionary, get_radioactivity

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
    lines = range(data_in['sets']['lines'])

    # we're assuming that each job in the same line has the same "type" but different from the other line.
    line_type = {line: line for line in lines}
    job_types_available = data_in['production']

    line_durations = {l: job_types_available[line_type[l]]['time'] for l in lines}
    max_jobs = {l: int(horizon_size / line_durations[line_type[l]]) for l in lines}

    # now we start creating the "job" variables.

    job_start_times_list = \
        {l:
         [job * time for job, time in zip(range(max_jobs[l]), max_jobs[l] * [line_durations[l]])]
         for l in line_durations
         }
    job_end_times_list = {l: [time + line_durations[l] for time in job_start_times_list[l]] for l in lines}

    # we get start times and end times with an additional job index (tuple line-job).
    job_start_time = {}
    job_end_times = {}
    for line in job_start_times_list:
        for job, value in enumerate(job_start_times_list[line]):
            job_start_time[line, job] = job_start_times_list[line][job]
            job_end_times[line, job] = job_end_times_list[line][job]

    job_type = {job: line_type[job[0]] for job in job_start_time}
    job_production = {job: job_types_available[job_type[job]]['dosages'] for job in job_start_time}
    job_initial_radio = {job: job_types_available[job_type[job]]['radio'] for job in job_start_time}

    #  ##################
    #  ##TRANSPORT#######
    #  ##################

    # trivial solution: each vehicle to one center.
    # here, we will take as much as vehicles as necessary (which is not okay...)
    vehicles = range(max(data_in['sets']['vehicles'], len(data_in['clients'])-1))
    arcs = data_in['travel'].keys()
    times_prod_to_center = {center: data_in['travel'][node1, center]['times'] for node1, center in arcs if node1 == 0}
    times_center_to_prod = {center: data_in['travel'][center, node1]['times'] for node1, center in arcs if node1 == 0}
    vehicle_to_center = {veh: veh+1 for veh in vehicles}
    duration_trip = {veh: times_prod_to_center[vehicle_to_center[veh]] + times_center_to_prod[vehicle_to_center[veh]]
                     for veh in vehicles}
    max_trips = {veh: int(horizon_size / duration_trip[veh]) for veh in vehicles}
    route_start_time = \
        {(veh, route): route * duration_trip[veh] for veh in vehicles for route in range(max_trips[veh])}
    routes = route_start_time.keys()
    # route_end_times = \
    #     {veh_route: route_start_time[veh_route] + duration_trip[veh_route[0]] for veh_route in routes}

    # arrivals are times when each route passes through each node in its path. Since the first node has no
    # vehicle (or route) assigned, we need to assume the starting time of the route is the arrival to the node0
    route_arrival = \
        {(veh_route, vehicle_to_center[veh_route[0]]):
             route_start_time[veh_route] + times_prod_to_center[vehicle_to_center[veh_route[0]]]
         for veh_route in routes}
    route_arrivals_node0 = \
        {(veh_route, 0): route_start_time[veh_route] for veh_route in routes}
    route_arrival.update(route_arrivals_node0)

    # Now that we have the routes, we can decide how much each route needs.
    # basically: all the consumption between consecutive routes.
    center_demand = data_in['demand']
    centers = data_in['clients'].keys()
    center_num_groups = {center: 0 for center in centers}
    for (center, pos), patient in center_demand.items():
        center_num_groups[center] += 1

    # I prepare an ordered list of routes per center:
    veh_routes_per_center = {}
    for center in centers:
        veh_routes_per_center[center] = [(veh, route) for (veh, route) in routes
                                         if ((veh, route), center) in route_arrival]
        veh_routes_per_center[center].sort(key=lambda x: route_arrival[x, center])

    #  ##################
    #  ##TRANSPORT/DEMAND
    #  ##################

    # I match patients with potential routes they could take
    # based on the route that goes to the center of the patient
    # and whether the patient is treated after the route arrives to the center
    route_patient = {(route, patient): 0 for route in routes for patient in center_demand}
    for center in centers:
        if len(veh_routes_per_center[center]) == 0:
            continue
        for route in veh_routes_per_center[center]:
            arrive_time = route_arrival[route, center]
            for pos in range(center_num_groups[center]):
                if arrive_time <= center_demand[(center, pos)]['min']:
                    route_patient[(route, (center, pos))] = 1
    route_patient = clean_dictionary(route_patient)
    # TODO: routes for the last hospital

    #  ##################
    #  #TRANSPORT/PRODUCE
    #  ##################

    # Now we tie transport with production... so that:
    # everything that is being produced gets into the vehicle as soon as possible.
    # but only until the vehicle is full with all the needed doses.
    # this means that I need to calculate the jobs that finished since the last trip
    # this is similar to the demand math but with

    # I first ordered jobs according to their start times.
    # but if we want to reduce the amount of lines being used
    # we probably want to order them according to the line and then start times.
    # jobs_ordered = sorted(list(job_start_time.keys()), key=lambda x: x[0]*10000 + job_start_time[x])
    jobs_ordered = sorted(list(job_start_time.keys()), key=lambda x: job_start_time[x])
    route_job_patient = {(route, job, patient): 0 for (route, patient) in route_patient for job in job_start_time}

    # in order to match production to routes to patients we need to:
    # 1. be sure the quality of the radioactive material is still good.
    # 2. be sure not to surpass the maximum production allowed.
    # keep track of what is being produced and stored.
    # 3. be sure to assign only production that ends before the route starts
    # 4. patient is not satisfied by any route.

    job_remain_production = {job: job_production[job] for job in job_start_time}
    patient_satisfied = {key: 0 for key in center_demand}
    max_radio = data_in['radio']['max']
    min_radio = data_in['radio']['min']
    ratio_radio = data_in['radio']['decay']

    for job in jobs_ordered:
        for route, patient in route_patient:
            # we do some math to check the radioactive decay
            time_first_patient = center_demand[patient]['min'] - job_end_times[job]
            time_last_patient = center_demand[patient]['max'] - job_end_times[job]

            radio_first_patient = get_radioactivity(job_initial_radio[job], time_first_patient, ratio_radio)
            radio_last_patient = get_radioactivity(job_initial_radio[job], time_last_patient, ratio_radio)

            # we do some checks to see if it makes sense to make the assignment:
            if not (radio_first_patient <= max_radio and radio_last_patient >= min_radio) or \
                job_remain_production[job] == 0 or \
                route_start_time[route] <= job_end_times[job] or \
                patient_satisfied[patient] != 0:
                continue

            # if this is a good candidate, then assign jobs, routes and patients:
            job_remain_production[job] -= center_demand[patient]['num']
            patient_satisfied[patient] = 1
            route_job_patient[route, job, patient] = 1

    route_job_patient = clean_dictionary(route_job_patient)

    # I only need to register the jobs that actually serve a patient:
    jobs_assigned = set([tup[1] for tup in route_job_patient])
    job_start_time = {job: time for job, time in job_start_time.items() if job in jobs_assigned}
    job_type = {job: j_type for job, j_type in job_type.items() if job in jobs_assigned}
    solution = {
        'jobs_start': job_start_time
        , 'jobs_type': job_type
        , 'routes_start': route_start_time
        , 'routes_visit': route_arrival
        , 'route_job_patient': route_job_patient
    }
    return solution