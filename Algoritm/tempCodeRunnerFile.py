
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
