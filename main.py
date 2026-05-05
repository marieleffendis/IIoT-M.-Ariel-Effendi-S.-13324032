from vision.hybrid_detector import HybridDetector
from logic.matcher import match_target
from logic.state_machine import StateMachine
from controller.system_controller import SystemController
from hardware.camera import get_frame
from hardware.conveyor import stop_conveyor, start_conveyor
from robot.controller import execute_robot

from config import MODEL_PATH

if __name__ == "__main__":
    system = SystemController()
    system.run()
# =====================
# INIT
# =====================
detector = HybridDetector(MODEL_PATH)
sm = StateMachine()

# dummy target (nanti dari image)
target_map = {
    "red": (0,0),
    "green": (1,1),
    "blue": (2,2),
    "yellow": (3,3)
}

# =====================
# LOOP
# =====================
while True:
    frame = get_frame()
    if frame is None:
        continue

    state = sm.get()

    if state == "IDLE":
        objects = detector.detect(frame)

        if objects:
            stop_conveyor()
            sm.set("PROCESS")

    elif state == "PROCESS":
        objects = detector.detect(frame)

        if not objects:
            sm.set("IDLE")
            continue

        commands = match_target(objects, target_map)

        for cmd in commands:
            execute_robot(cmd)

        sm.set("RETURN")

    elif state == "RETURN":
        start_conveyor()
        sm.set("IDLE")