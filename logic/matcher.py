def match_target(objects, target_map):
    commands = []

    for obj in objects:
        color = obj["color"]

        if color not in target_map:
            continue

        commands.append({
            "pick_pixel": obj["pixel"],
            "place_grid": target_map[color]
        })

    return commands