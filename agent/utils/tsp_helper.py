import os
import requests
import googlemaps
import streamlit as st
import folium
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from folium.plugins import AntPath, MarkerCluster
from datetime import datetime

GOOGLE_KEY = st.secrets.get("GOOGLE_KEY")
GMAPS = googlemaps.Client(key=GOOGLE_KEY)

# ------------------------
# 1. Get distance matrix from Google Maps
# ------------------------
# def get_distance_matrix(locations):
#     """
#     locations: list of (lat, lon)
#     returns: distance matrix in meters
#     """
#     origins = "|".join([f"{lat},{lon}" for lat, lon in locations])
#     destinations = origins

#     url = f"https://maps.googleapis.com/maps/api/distancematrix/json?units=metric&origins={origins}&destinations={destinations}&key={GOOGLE_KEY}"
    
#     response = requests.get(url)
#     result = response.json()

#     n = len(locations)
#     matrix = [[0]*n for _ in range(n)]

#     for i, row in enumerate(result["rows"]):
#         for j, elem in enumerate(row["elements"]):
#             matrix[i][j] = elem["distance"]["value"]  # meters
    
#     return matrix


def get_distance_matrix(locations):
    """
    Builds a distance matrix using Google Maps Directions API.
    
    Args:
        locations (list of (lat, lon)): List of coordinates.
    
    Returns:
        list[list[int]]: Distance matrix in meters.
    """
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    now = datetime.now()

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 0
            else:
                origin = f"{locations[i][0]},{locations[i][1]}"
                destination = f"{locations[j][0]},{locations[j][1]}"

                directions_result = GMAPS.directions(
                    origin=origin,
                    destination=destination,
                    mode="driving",
                    departure_time=now
                )
                if directions_result:
                    leg = directions_result[0]['legs'][0]
                    matrix[i][j] = leg['distance']['value']  # meters
                else:
                    matrix[i][j] = float("inf")  # fallback if no route
    return matrix

# ------------------------
# 2. Solve TSP with OR-Tools
# ------------------------
def solve_tsp(distance_matrix):
    data = {
        'distance_matrix': distance_matrix,
        'num_vehicles': 1,
        'depot': 0
    }

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix),
                                           data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        index = routing.Start(0)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        return route
    else:
        return None


def get_directions(start, end):
    """
    Retrieves directions from the Google Maps Directions API.

    Args:
        start (str): The starting location for the route.
        end (str): The ending location for the route.

    Returns:
        list: A list of directions results.
    """
    directions_result = GMAPS.directions(start, end, mode="driving", departure_time="now")
    return directions_result

def extract_info(directions_result):
    """
    Extracts information such as duration, distance, and instructions from the directions result.

    Args:
        directions_result (list): The directions result from the Google Maps Directions API.

    Returns:
        tuple: A tuple containing the duration, distance, instructions, and steps.
    """
    leg = directions_result[0]['legs'][0]
    duration = leg['duration']['text']    
    distance = leg['distance']['text']
    instructions = []
    steps = []
    for step in leg['steps']:
        instruction = step['html_instructions']
        instructions.append(instruction)
        steps.append(step)
    return duration, distance, instructions, steps

def plot_route(folium_map, directions_result, steps):
    """
    Plots the route on the Folium map without adding markers for each instruction.
    Only the animated line for the route is drawn.
    """
    route_points = []
    for step in steps:
        polyline = step['polyline']['points']
        points = decode_polyline(polyline)
        route_points.extend(points)
    
    # Add animated line for the main route
    AntPath(route_points, color="blue", weight=2.5, opacity=1).add_to(folium_map)


def decode_polyline(polyline_str):
    """
    Decodes a polyline that is encoded using the Google Maps method.

    Args:
        polyline_str (str): The encoded polyline string.

    Returns:
        list: A list of tuples representing the decoded latitude and longitude coordinates.
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    while index < len(polyline_str):
        for key in changes.keys():
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[key] = ~(result >> 1)
            else:
                changes[key] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']
        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates


def show_tsp_route_on_map(locations, route):
    """
    Generates a Folium map showing the TSP route following real streets using Google Directions API.
    Stop 0 (depot) has a special marker, others are different.
    """
    if not route or len(route) < 2:
        return None

    # Center the map at the average location
    mid_lat = sum([loc[0] for loc in locations]) / len(locations)
    mid_lon = sum([loc[1] for loc in locations]) / len(locations)
    folium_map = folium.Map(location=[mid_lat, mid_lon], zoom_start=12)

    # Draw route lines for each leg
    for i in range(len(route) - 1):
        start_idx = route[i]
        end_idx = route[i + 1]
        start = f"{locations[start_idx][0]},{locations[start_idx][1]}"
        end = f"{locations[end_idx][0]},{locations[end_idx][1]}"
        
        directions_result = get_directions(start, end)
        _, _, _, steps = extract_info(directions_result)
        plot_route(folium_map, directions_result, steps)
    
    # Add markers for TSP stops
    depot_idx = route[0]  # The first stop (depot)
    for idx in route:
        lat, lon = locations[idx]
        if idx == depot_idx:
            # Special marker for depot
            folium.Marker(
                [lat, lon],
                popup=f"Depot / Start (Stop {idx})",
                icon=folium.Icon(color="green", icon="home")
            ).add_to(folium_map)
        else:
            # Regular markers for other stops
            folium.Marker(
                [lat, lon],
                popup=f"Stop {idx}",
                icon=folium.Icon(color="red", icon="flag")
            ).add_to(folium_map)

    # Optional: add map tile layers
    folium.TileLayer('cartodbdark_matter', attr='Carto').add_to(folium_map)
    folium.TileLayer('cartodbpositron', attr='Carto').add_to(folium_map)
    folium.LayerControl().add_to(folium_map)

    return folium_map

# ------------------------
# 3. Example usage
# ------------------------
if __name__ == "__main__":
    # Example locations: Mexico City landmarks
    locations = [
    (19.4326, -99.1332),  # Zócalo
    (19.3550, -99.1730),  # UNAM, Coyoacán
    (19.7020, -99.1920),  # Satélite, Estado de México
    (19.4978, -99.1269),  # Basilica de Guadalupe
    (19.3100, -99.5380)   # Ciudad de México sur-oeste (Mixcoac / Periférico)
]
    

    distance_matrix = get_distance_matrix(locations)
    route = solve_tsp(distance_matrix)

    print("Optimal Route (index order):", route)
    print("Visit order (coordinates):")
    for idx in route:
        print(locations[idx])
    
    # Show TSP route on map
    tsp_map = show_tsp_route_on_map(locations, route)
    if tsp_map:
        tsp_map.save("tsp_route_map.html")
        print("TSP route map saved as 'tsp_route_map.html'.")