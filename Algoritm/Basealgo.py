import random
import time  # Import time for delay
from db_export import export_to_website_models

# -----------------------------
# Grid and simulation settings
# -----------------------------
SIZE = 4
CYCLE_TIME = 120
MIN_GREEN = 15
YELLOW_TIME = 3
CAPACITY_THRESHOLD = 10  # outgoing lane threshold

DIRS = ['N', 'S', 'E', 'W']
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

# Turn mapping
TURN_MAP = {
    'N': {'straight': 'S', 'left': 'E', 'right': 'W'},
    'S': {'straight': 'N', 'left': 'W', 'right': 'E'},
    'E': {'straight': 'W', 'left': 'N', 'right': 'S'},
    'W': {'straight': 'E', 'left': 'S', 'right': 'N'}
}

# -----------------------------
# Nodes initialization
# -----------------------------
nodes = [chr(ord('A') + i) for i in range(SIZE*SIZE)]
node_pos = {nodes[r*SIZE + c]: (r,c) for r in range(SIZE) for c in range(SIZE)}
pos_node = {v:k for k,v in node_pos.items()}

def initialize_grid():
    """Create a new random traffic grid."""
    grid = {}
    for n in nodes:
        r, c = node_pos[n]
        neighbors = {}
        if r > 0: neighbors['N'] = pos_node[(r-1, c)]
        if r < SIZE-1: neighbors['S'] = pos_node[(r+1, c)]
        if c > 0: neighbors['W'] = pos_node[(r, c-1)]
        if c < SIZE-1: neighbors['E'] = pos_node[(r, c+1)]

        queues = {d: {d2: random.randint(0, 20) for d2 in DIRS if d2 != d} for d in DIRS}

        grid[n] = {
            'neighbors': neighbors,
            'queues': queues,
            'phase_times': {},
            'timeline': [],
            'lane_allowance': {},
            'blocked_phases': [],
            'green_lanes': [],
            'total_vehicles': sum(sum(q.values()) for q in queues.values())
        }
    return grid

# -----------------------------
# Helper functions
# -----------------------------
def is_outgoing_blocked(grid, node, from_dir, to_dir):
    dest = grid[node]['neighbors'].get(to_dir)
    if not dest: 
        return False
    arrival_dir = OPPOSITE[to_dir]
    dest_queues = grid[dest]['queues'].get(arrival_dir, {})
    total_waiting = sum(dest_queues.values())
    return total_waiting >= CAPACITY_THRESHOLD

def allocate_dynamic_cycle(grid, node):
    data = grid[node]
    queues = data['queues']

    phases = [
        ('ns_main', ['N','S'], ['straight','left']),
        ('ew_main', ['E','W'], ['straight','left']),
        ('ns_right', ['N','S'], ['right']),
        ('ew_right', ['E','W'], ['right'])
    ]

    # Compute demand per phase
    phase_demand = {p[0]: 0 for p in phases}
    for p_name, dirs, turn_types in phases:
        for from_dir in dirs:
            for t in turn_types:
                to_dir = TURN_MAP[from_dir].get(t)
                if not to_dir: continue
                num = queues.get(from_dir, {}).get(to_dir, 0)
                phase_demand[p_name] += num

    active_phases = [k for k,v in phase_demand.items() if v>0]
    if not active_phases:
        data['phase_times'] = {k:0 for k in phase_demand}
        return

    total_demand = sum(phase_demand[p] for p in active_phases)
    total_usable_green = max(0, CYCLE_TIME - len(active_phases)*YELLOW_TIME)

    # Initial proportional allocation
    phase_times = {}
    for p in phase_demand:
        if phase_demand[p] > 0:
            raw = (phase_demand[p]/total_demand)*total_usable_green
            phase_times[p] = max(MIN_GREEN, int(round(raw)))
        else:
            phase_times[p] = 0

    # Adjust remainder
    allocated = sum(phase_times[p] for p in phase_times)
    remainder = total_usable_green - allocated
    if remainder != 0:
        ordered = sorted(active_phases, key=lambda x: phase_demand[x], reverse=True)
        i = 0
        while remainder != 0 and ordered:
            phase_times[ordered[i%len(ordered)]] += (1 if remainder>0 else -1)
            remainder = total_usable_green - sum(phase_times[p] for p in phase_times)
            i += 1

    # Lane allowance & green lanes
    lane_allowance = {}
    green_lanes = []
    blocked_phases = set()
    for p_name, dirs, turn_types in phases:
        lane_allowed = False
        for from_dir in dirs:
            for t in turn_types:
                to_dir = TURN_MAP[from_dir].get(t)
                if not to_dir: continue
                cars = queues.get(from_dir, {}).get(to_dir, 0)
                blocked = is_outgoing_blocked(grid, node, from_dir, to_dir) and cars>0
                allowed = (cars>0) and not blocked
                lane_allowance.setdefault(from_dir, {})[to_dir] = allowed
                if allowed:
                    lane_allowed = True
                    green_lanes.append((from_dir, to_dir))
                    dest = data['neighbors'].get(to_dir)
                    if dest:
                        grid[dest].setdefault('green_lanes', []).append((OPPOSITE[to_dir], OPPOSITE[from_dir]))
        if not lane_allowed:
            blocked_phases.add(p_name)

    # Redistribute blocked phase times
    usable_phases = [p for p in phase_times if p not in blocked_phases and phase_times[p]>0]
    locked_out_time = sum(phase_times[p] for p in blocked_phases)
    if locked_out_time > 0 and usable_phases:
        usable_demand = sum(phase_demand[p] for p in usable_phases)
        for p in usable_phases:
            add = int(round((phase_demand[p]/usable_demand)*locked_out_time)) if usable_demand>0 else 0
            phase_times[p] += add
    for p in blocked_phases: phase_times[p]=0

    # Build timeline
    timeline = []
    cur = 0
    for p_name, dirs, turn_types in phases:
        g = phase_times.get(p_name, 0)
        if g > 0:
            timeline.append((p_name, cur, cur+g))
            cur += g
            cur += YELLOW_TIME

    data['phase_times'] = phase_times
    data['timeline'] = timeline
    data['lane_allowance'] = lane_allowance
    data['blocked_phases'] = list(blocked_phases)
    data['green_lanes'] = green_lanes
    data['total_vehicles'] = sum(sum(q.values()) for q in queues.values())

# -----------------------------
# Print phase chart for a node
# -----------------------------
def print_cycle_chart(grid, node):
    data = grid[node]
    print(f"\nNode {node} cycle (CYCLE={CYCLE_TIME}s, MIN={MIN_GREEN}s, YELLOW={YELLOW_TIME}s):")
    print(f"Total vehicles at node: {data['total_vehicles']}")

    phases = [
        ('ns_main', ['N','S'], ['straight','left']),
        ('ew_main', ['E','W'], ['straight','left']),
        ('ns_right', ['N','S'], ['right']),
        ('ew_right', ['E','W'], ['right'])
    ]

    for p_name, dirs, turn_types in phases:
        g_start_end = next(((name, s, e) for name, s, e in data['timeline'] if name == p_name), None)
        if not g_start_end:
            continue
        _, start, end = g_start_end
        print(f"Phase {p_name} [{start}s -> {end}s]")

        for from_dir in dirs:
            for turn_type in turn_types:
                to_dir = TURN_MAP[from_dir].get(turn_type)
                if not to_dir or from_dir not in data['queues']: 
                    continue
                cars = data['queues'][from_dir].get(to_dir,0)
                allowed = data['lane_allowance'].get(from_dir, {}).get(to_dir, False)
                sig = 'GREEN' if allowed else 'RED'
                print(f"  {from_dir:<3} {turn_type:<8} -> {to_dir:<3}: {sig} ({cars} cars)")

# -----------------------------
# Simulation step
# -----------------------------
def simulate_step(grid):
    for n in nodes:
        allocate_dynamic_cycle(grid, n)

# -----------------------------
# Main loop for 10 steps every 10 sec
# -----------------------------
def main():
    for step in range(1, 11):  # Maximum 10 iterations
        print(f"\n=== Step {step} ===")
        grid = initialize_grid()  # Generate new traffic randomly each step
        simulate_step(grid)
        for n in nodes:
            print_cycle_chart(grid, n)
        # Export to MongoDB after each step
        export_to_website_models(grid, nodes, node_pos, section_name=f"Grid Step {step}", location="Sector 5, City")
        time.sleep(10)  # Wait 10 seconds before next iteration

if __name__ == "__main__":
    main()
