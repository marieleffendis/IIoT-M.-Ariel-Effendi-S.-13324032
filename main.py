import argparse

from vision.hybrid_detector import HybridDetector
from logic.matcher import match_target
from logic.state_machine import StateMachine
from controller.system_controller import SystemController
from hardware.camera import get_frame
from hardware.conveyor import stop_conveyor, start_conveyor
from robot.controller import execute_robot, move_to_grid

from config import MODEL_PATH


def run_manual(col, row):
    """Gerakkan robot ke posisi grid (col, row) secara langsung."""
    print(f"[MANUAL] Pindah ke grid ({col},{row})")
    move_to_grid(col, row)


def run_detection_loop():
    """Loop deteksi otomatis tanpa MQTT (mode sederhana)."""
    detector   = HybridDetector(MODEL_PATH)
    sm         = StateMachine()
    target_map = {
        "red"   : (1, 1),
        "green" : (2, 2),
        "blue"  : (3, 3),
        "yellow": (4, 4),
    }

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


def run_controller():
    """Jalankan SystemController lengkap dengan MQTT."""
    system = SystemController()
    system.run()


def main():
    parser = argparse.ArgumentParser(description="IIoT Dobot Magician — entrypoint")
    parser.add_argument(
        "--manual", nargs=2, metavar=("COL", "ROW"),
        help="Gerakkan robot ke posisi grid (1-indexed, mis: --manual 1 1)"
    )
    parser.add_argument(
        "--controller", action="store_true",
        help="Jalankan SystemController lengkap (dengan MQTT)"
    )
    args = parser.parse_args()

    if args.manual:
        col, row = int(args.manual[0]), int(args.manual[1])
        if not (1 <= col <= 4 and 1 <= row <= 4):
            print(f"[ERROR] col dan row harus antara 1–4. Diberikan: col={col}, row={row}")
            return
        run_manual(col, row)
        return

    if args.controller:
        run_controller()
        return

    run_detection_loop()


if __name__ == "__main__":
    main()