import random

# -----------------------------
# --- CONFIGURATION & CONSTANTS ---
# -----------------------------
SIZE = 8
CYCLE_TIME = 120
MIN_GREEN = 5
YELLOW_TIME = 5
SATURATION_FLOW_RATE = 0.5

TURN_PROBS = {'straight': 0.7, 'left': 0.15, 'right': 0.15}
DIRS = ['N', 'E', 'S', 'W']
OPPOSITE = {'N':'S', 'E':'W', 'S':'N', 'W':'E'}

# Using Indian (left-hand drive) logic
TURN_MAP = {
    'N': {'left': 'E', 'straight': 'S', 'right': 'W'},
    'E': {'left': 'S', 'straight': 'W', 'right': 'N'},
    'S': {'left': 'W', 'straight': 'N', 'right': 'E'},
    'W': {'left': 'N', 'straight': 'E', 'right': 'S'}
}

# Global State Variables
nodes, node_pos, pos_node, grid = [], {}, {}, {}

# -----------------------------
# --- HELPER FUNCTION ---
# -----------------------------

def get_turn_type(from_dir, to_dir):
    """Safely determines the turn type (left, right, straight)."""
    for turn_name, dest_dir in TURN_MAP[from_dir].items():
        if dest_dir == to_dir:
            return turn_name
    return None

# -----------------------------
# --- SETUP AND INITIALIZATION ---
# -----------------------------

def initialize_grid():
    """Sets up the grid and populates each turning direction with random traffic."""
    global nodes, node_pos, pos_node, grid
    
    nodes = [chr(ord('A') + i) for i in range(SIZE*SIZE)]
    
    node_pos = {nodes[r*SIZE + c]: (r,c) for r in range(SIZE) for c in range(SIZE)}
    pos_node = {v:k for k,v in node_pos.items()}
    grid = {}

    for n in nodes:
        r,c = node_pos[n]
        neighbors = {
            'N': pos_node.get((r-1, c)), 'E': pos_node.get((r, c+1)),
            'S': pos_node.get((r+1, c)), 'W': pos_node.get((r, c-1))
        }
        neighbors = {d: node for d, node in neighbors.items() if node is not None}
        
        queues = {}
        # For each possible incoming lane...
        for from_dir in neighbors.keys():
            queues[from_dir] = {}
            # ... and for each possible turn from that lane...
            possible_turns = TURN_MAP[OPPOSITE[from_dir]]
            for turn_type in ['straight', 'left', 'right']:
                to_dir = possible_turns.get(turn_type)
                # ... generate a random number of cars.
                if to_dir in neighbors:
                    num_cars = random.randint(0, 20)
                    if num_cars > 0:
                        queues[from_dir][to_dir] = num_cars
        
        grid[n] = {'queues': queues, 'green': {}, 'signals': {}, 'neighbors': neighbors}


# -----------------------------
# --- CORE ALGORITHMS ---
# -----------------------------

def allocate_green_indian_model(node):
    """Implements the smart, 4-stage proportional model for Indian traffic."""
    data = grid[node]
    data['green'], data['signals'] = {}, {}
    
    phases = {
        'ns_right': {'dirs': ['N', 'S'], 'turns': ['right']}, 'ns_main': {'dirs': ['N', 'S'], 'turns': ['straight', 'left']},
        'ew_right': {'dirs': ['E', 'W'], 'turns': ['right']}, 'ew_main': {'dirs': ['E', 'W'], 'turns': ['straight', 'left']}
    }
    phase_demands = {name: 0 for name in phases}
    
    for from_dir, turns in data['queues'].items():
        for to_dir, cars in turns.items():
            turn_type = get_turn_type(OPPOSITE[from_dir], to_dir)
            if turn_type:
                phase_key = ('ns_' if from_dir in ['N','S'] else 'ew_') + ('right' if turn_type == 'right' else 'main')
                phase_demands[phase_key] += cars

    total_demand = sum(phase_demands.values())
    if total_demand == 0: return

    active_phases = sum(1 for demand in phase_demands.values() if demand > 0)
    total_usable_green = CYCLE_TIME - (active_phases * YELLOW_TIME)

    phase_times = {name: int(max(MIN_GREEN, (demand / total_demand) * total_usable_green)) if demand > 0 else 0 for name, demand in phase_demands.items()}

    for phase_name, g_time in phase_times.items():
        if g_time > 0:
            for from_dir in phases[phase_name]['dirs']:
                for turn_type in phases[phase_name]['turns']:
                    to_dir = TURN_MAP[OPPOSITE[from_dir]].get(turn_type)
                    if from_dir in data['queues'] and to_dir in data['queues'][from_dir]:
                        if from_dir not in data['green']: data['green'][from_dir] = {}
                        if from_dir not in data['signals']: data['signals'][from_dir] = {}
                        data['green'][from_dir][to_dir] = g_time
                        data['signals'][from_dir][to_dir] = 'GREEN'

def simulate_step():
    """Orchestrates a full simulation step with instant movement."""
    moves = []

    for n in nodes:
        allocate_green_indian_model(n)
        
    for n in nodes:
        data = grid[n]
        for from_dir, turns in data.get('green', {}).items():
            for to_dir, green_time in turns.items():
                if from_dir in data['queues'] and to_dir in data['queues'].get(from_dir, {}):
                    queue_cars = data['queues'][from_dir][to_dir]
                    moved = min(queue_cars, int(green_time * SATURATION_FLOW_RATE))
                    if moved > 0:
                        data['queues'][from_dir][to_dir] -= moved
                        destination_node = data['neighbors'][to_dir]
                        arrival_dir = OPPOSITE[to_dir]
                        moves.append((destination_node, arrival_dir, moved))
    
    for destination_node, arrival_dir, num_cars in moves:
        if arrival_dir not in grid[destination_node]['queues']:
            grid[destination_node]['queues'][arrival_dir] = {}
        p_turns = TURN_MAP[OPPOSITE[arrival_dir]]
        for turn_t, turn_prob in TURN_PROBS.items():
            turn_d = p_turns.get(turn_t)
            if turn_d in grid[destination_node]['neighbors']:
                num_c = int(num_cars * turn_prob)
                if num_c > 0:
                    grid[destination_node]['queues'][arrival_dir][turn_d] = grid[destination_node]['queues'][arrival_dir].get(turn_d, 0) + num_c

def print_report(step):
    """Prints a report showing all existing lanes for every node."""
    print(f"\n\n{'='*20} Step {step} Report {'='*20}")
    
    for n in sorted(nodes):
        data = grid[n]
        print(f"\n--- Node {n} ---")
        
        has_traffic = False
        for from_dir in sorted(data['neighbors'].keys()):
            actual_from_dir = OPPOSITE[from_dir]
            queues = data['queues'].get(actual_from_dir, {})
            total_cars = sum(queues.values())
            
            green_time = next((t for t in data['green'].get(actual_from_dir, {}).values() if t > 0), 0)
            
            print(f"  Lane {actual_from_dir}: Cars Waiting = {total_cars}, Green Time = {green_time}s")
            if total_cars > 0:
                has_traffic = True
            
            possible_turns = TURN_MAP[actual_from_dir]
            for turn_type in ['straight', 'left', 'right']:
                to_dir = possible_turns.get(turn_type)
                if to_dir in data['neighbors']:
                    cars = queues.get(to_dir, 0)
                    signal = data['signals'].get(actual_from_dir, {}).get(to_dir, 'RED')
                    green_time_turn = data['green'].get(actual_from_dir, {}).get(to_dir, 0)
                    print(f"    -> To {to_dir}: {cars:<3} cars | Signal: {signal} ({green_time_turn}s)")
        
        if not has_traffic:
            print("  No traffic at this intersection.")

# -----------------------------
# --- MAIN EXECUTION ---
# -----------------------------
if __name__ == '__main__':
    initialize_grid()
    print("--- Simulation Start: Grid initialized with random traffic ---")

    print_report(step=0) # Show initial random state

    print("\n--- Running Simulation for 1 Step ---")
    simulate_step()
    
    print_report(step=1) # Show state after one step