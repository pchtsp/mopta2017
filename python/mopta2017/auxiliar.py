
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
