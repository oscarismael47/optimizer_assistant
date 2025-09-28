from datetime import datetime
from typing import List, Annotated, Any, Tuple
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import interrupt, Command
from langchain_core.messages import ToolMessage
try:
    from utils.tsp_helper import get_distance_matrix, solve_tsp, show_tsp_route_on_map
except:
    from agent.utils.tsp_helper import get_distance_matrix, solve_tsp, show_tsp_route_on_map
    
@tool("tsp_solver")
def tsp_solver(reasoning: str,
               tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Traveling Salesperson Problem (TSP) Solver Tool.

    This tool computes the optimal route for a set of locations 
    minimizing travel distance or time. It is called automatically 
    when the user's problem can be modeled as a TSP.

    Parameters
    ----------
    reasoning : str
    
    tool_call_id : str
        The injected ID for the current tool call, used for tracking and state updates.

    Returns
    -------
    Command
        A command that updates the conversation state with the computed route.
    """

    # Ask user for missing inputs 
    locations = interrupt(value = f"""{reasoning}\n\nI need these additional details:\n\n1.  The origin location\n2. The list of locations you want to visit\n""")

    distance_matrix = get_distance_matrix(locations)
    route = solve_tsp(distance_matrix)
    tsp_map = show_tsp_route_on_map(locations, route)

    now = datetime.now()
    now_str = now.strftime("%Y_%m_%d_%H_%M_%S_%f")[:-3]

    tsp_map_path = f"out/tsp_route_map_{now_str}.html"
    if tsp_map:
        tsp_map.save(tsp_map_path)
    optimal_route = "Visit order (coordinates):n"
    for i, idx in enumerate(route):
        optimal_route += f"- {i} Coordinate: {locations[idx]}\n"
    optimal_route += "A Map with the TSP response has been generated too"
    return Command(update={
        "solution": {"optimal_route":optimal_route,
                     "tsp_map_path":tsp_map_path},
        "messages": [
            ToolMessage({
                         "optimal_route":optimal_route,
                          "tsp_map_path":tsp_map_path
                        }, 
                        tool_call_id=tool_call_id)
        ]
    }) # reference:  https://langchain-ai.github.io/langgraph/how-tos/tool-calling/?_gl=1*1rfn5oz*_gcl_au*MTIxNjc5NTc5Ny4xNzUyMDkzMDY2*_ga*MzU1ODY4ODkzLjE3NTIwOTMwNjY.*_ga_47WX3HKKY2*czE3NTc1MTQ4ODIkbzQxJGcxJHQxNzU3NTE1OTE5JGo2MCRsMCRoMA..#short-term-memory



@tool("bin_packing_solver")
def bin_packing_solver(reasoning: str,
                       pallet_dimensions: Tuple[int, int],   # (width, height)
                        pallet_number: int,                   # cantidad de pallets
                        container_dimensions: Tuple[int, int],# (width, height)
                       tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Bin Packing Solver Tool.

    This tool computes the optimal packing of pallets into containers.

    Parameters
    ----------
    reasoning : str
        Description of the packing problem.
    pallet_dimensions : tuple(int, int)
        Pallet size (width, height).
    pallet_number : int
        Number of pallets of this type.
    container_dimensions : tuple(int, int)
        Container size (width, height).
    tool_call_id : str
        Internal tracking ID for this tool call.

    Returns
    -------
    Command
        A command with the computed bin packing solution.
    """

    # Ask user for required details if missing
    packing_request = interrupt(value=f"""{reasoning}\n\nI need these details:\n
1. Pallet dimensions and quantities (example: 10 pallets 80x120, 5 pallets 100x120)\n
2. Container size (example: 235x590 for a 20' container)\n""")

    # Example structure expected:
    # packing_request = {
    #   "pallets": [(create_pallet(80,120,5), 10), (create_pallet(100,120,5), 5)],
    #   "container": create_container(235,590)
    # }

    pallets = packing_request["pallets"]
    container = packing_request["container"]

    all_rects, all_pals, summary = solver(pallets, container)

    # Prepare response
    now = datetime.now()
    now_str = now.strftime("%Y_%m_%d_%H_%M_%S_%f")[:-3]

    packing_result = "\n".join(summary)
    packing_result += "\nA bin packing solution has been computed."

    return Command(update={
        "solution": {
            "packing_summary": packing_result,
            "rectangles": all_rects
        },
        "messages": [
            ToolMessage({
                "packing_summary": packing_result,
                "rectangles": str(all_rects)
            }, tool_call_id=tool_call_id)
        ]
    })