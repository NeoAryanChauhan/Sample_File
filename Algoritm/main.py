from Basealgo import initialize_grid, simulate_step, print_report, grid, nodes
from db_export import export_step_to_db

if __name__ == '__main__':
    initialize_grid()
    print("--- Simulation Start: Grid initialized with random traffic ---")
    print_report(step=0)
    export_step_to_db(step=0, grid=grid, nodes=nodes)

    print("\n--- Running Simulation for 1 Step ---")
    simulate_step()
    print_report(step=1)
    export_step_to_db(step=1, grid=grid, nodes=nodes)