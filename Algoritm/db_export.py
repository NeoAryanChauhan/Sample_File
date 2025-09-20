from db_connect import get_db
import datetime

def export_step_to_db(step, grid, nodes):
    db = get_db()
    collection = db['simulation_steps']
    step_data = []
    for n in nodes:
        data = grid[n]
        step_data.append({
            'node': n,
            'queues': data['queues'],
            'green': data['green'],
            'signals': data['signals'],
            'neighbors': data['neighbors'],
            'step': step
        })
    if step_data:
        collection.insert_many(step_data)
    print(f"Step {step} data exported to simulation_steps.")

def export_to_website_models(grid, nodes, node_pos, section_name="Grid 1", location="Unknown"):
    db = get_db()
    section = {
        "name": section_name,
        "location": location,
        "status": "Active",
        "trafficLevel": "Medium",
        "nodes": [],
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": datetime.datetime.utcnow()
    }
    section_id = db.TrafficSection.insert_one(section).inserted_id

    node_ids = []
    for n in nodes:
        data = grid[n]
        row, col = node_pos[n]
        total_cars = sum(sum(turns.values()) for turns in data['queues'].values())
        jam = any(sum(turns.values()) > 15 for turns in data['queues'].values())
        active_signal = max(
            data.get('phase_times', {}).items(),
            key=lambda item: item[1] if isinstance(item[1], int) else 0,
            default=('North', 0)
        )[0].capitalize() if data.get('phase_times') else 'North'
        lanes = {}
        for dir in ['north', 'south', 'east', 'west']:
            dir_key = dir[0].upper()
            lanes[dir] = {
                "incoming": {
                    "open": True,
                    "flowRate": sum(data['queues'].get(dir_key, {}).values()),
                    "direction": "incoming"
                },
                "outgoing": {
                    "open": True,
                    "flowRate": 0,
                    "direction": "outgoing"
                }
            }
        node_doc = {
            "name": n,
            "sectionId": section_id,
            "row": row,
            "col": col,
            "activeSignal": active_signal,
            "jam": jam,
            "trafficFlow": total_cars,
            "lanes": lanes,
            "createdAt": datetime.datetime.utcnow(),
            "updatedAt": datetime.datetime.utcnow()
        }
        node_id = db.TrafficNode.insert_one(node_doc).inserted_id
        node_ids.append(node_id)
    db.TrafficSection.update_one({"_id": section_id}, {"$set": {"nodes": node_ids}})
    print(f"TrafficSection and {len(node_ids)} TrafficNodes exported to MongoDB.")

# Dummy implementations for missing functions and variables
def initialize_grid():
    global grid, nodes, node_pos
    # Example grid, nodes, and node_pos for demonstration
    grid = {
        'A': {
            'queues': {'N': {'L': 2, 'S': 3}, 'S': {'L': 1, 'S': 2}},
            'green': 'N',
            'signals': {'N': True, 'S': False},
            'neighbors': ['B'],
            'phase_times': {'North': 10, 'South': 5}
        }
    }
    nodes = ['A']
    node_pos = {'A': (0, 0)}

def print_report(step):
    print(f"Report for step {step}")

def simulate_step():
    # Example: increment queue values to simulate traffic
    for node in nodes:
        for dir_queues in grid[node]['queues'].values():
            for k in dir_queues:
                dir_queues[k] += 1

if __name__ == '__main__':
    initialize_grid()
    print("--- Simulation Start: Grid initialized with random traffic ---")
    print_report(step=0)
    export_step_to_db(step=0, grid=grid, nodes=nodes)

    print("\n--- Running Simulation for 1 Step ---")
    simulate_step()
    print_report(step=1)
    export_step_to_db(step=1, grid=grid, nodes=nodes)

    export_to_website_models(grid, nodes, node_pos, section_name="Grid 1", location="Sector 5, City")