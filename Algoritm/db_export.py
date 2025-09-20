from db_connect import get_db

def export_step_to_db(step, grid, nodes):
    db = get_db()
    collection = db['simulation_steps']
    step_data = []
    for n in nodes:
        data = grid[n]
        node_info = {
            'node': n,
            'queues': data['queues'],
            'green': data['green'],
            'signals': data['signals'],
            'neighbors': data['neighbors'],
            'step': step
        }
        step_data.append(node_info)
    collection.insert_many(step_data)