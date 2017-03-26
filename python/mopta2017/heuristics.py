def initial_solution(data_in):

    # let's make every production line to produce something in parallel.
    start_time = 0  # start of day
    end_time = 24*60  # end of day
    horizon_size = end_time - start_time

    # ##################
    # ##PRODUCTION######
    # ##################
    # each line has to have a maximum number of jobs in horizon
    lines = data_in['production'].keys()
    line_durations = {l: data_in['production'][l].p for l in lines}
    max_jobs = {l: int(horizon_size / line_durations[l]) for l in lines}
    start_times = \
        {l:
         [job * time for job, time in zip(range(max_jobs[l]), max_jobs[l] * [line_durations[l]])]
         for l in line_durations
         }
    end_times = {l: [time + line_durations[l] for time in start_times[l]] for l in lines}

    # we get start times and end times with an additional job index (tuple line-job).
    start_times_dict = {}
    end_times_dict = {}
    for line in start_times:
        for job, value in enumerate(start_times[line]):
            start_times_dict[line, job] = start_times[line][job]
            end_times_dict[line, job] = end_times[line][job]

    #  ##################
    #  ##TRANSPORT#######
    #  ##################

    # trivial solution: each vehicle to one center.
    vehicles = range(int(data_in['V']))
    arcs = data_in['travel'].keys()
    times_to_center = {center: data_in['travel'][node1, center].times for node1, center in arcs if node1 == 0}
    vehicle_to_center = {veh: veh+1 for veh in vehicles}
    duration_trip = {veh: times_to_center[vehicle_to_center[veh]]*2 for veh in vehicles}
    max_trips = {veh: int(horizon_size  / duration_trip[veh]) for veh in vehicles}
    veh_start_times_dict = \
        {(veh, route): max_trips[veh] for veh in vehicles for route in range(max_trips[veh])}

