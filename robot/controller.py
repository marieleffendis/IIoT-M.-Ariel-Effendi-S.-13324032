from robot.kinematics import grid_to_world

def execute_robot(cmd):
    pick_x, pick_y = cmd["pick_pixel"]
    row, col = cmd["place_grid"]

    place_x, place_y = grid_to_world(row, col)

    print(f"[ROBOT] PICK at pixel: {pick_x},{pick_y}")
    print(f"[ROBOT] PLACE at mm: {place_x},{place_y}")