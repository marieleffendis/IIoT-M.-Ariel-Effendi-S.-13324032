import json
import time

from vision.hybrid_detector import HybridDetector
from logic.matcher import match_target

from hardware.camera import get_frame
from hardware.conveyor import stop_conveyor, start_conveyor
from robot.controller import execute_robot

from comms.mqtt_client import MQTTClient
from comms.topics import *

from hmi.hmi_handler import HMIHandler
from config import MODEL_PATH


class SystemController:
    def __init__(self):
        self.detector = HybridDetector(MODEL_PATH)
        self.hmi = HMIHandler()

        self.mqtt = MQTTClient()
        self.setup_mqtt()

        self.state = "IDLE"
        self.last_objects = []
        self.start_time = time.time()
        self.state_start_time = time.time()
        self.state_durations = {
            "IDLE": 0.0,
            "PROCESS": 0.0,
            "RETURN": 0.0
        }
        self.color_counts = {
            "red": 0,
            "green": 0,
            "blue": 0,
            "yellow": 0
        }
        self.total_processed = 0

    # =========================
    # METRICS HELPERS
    # =========================
    def enter_state(self, new_state):
        now = time.time()
        self.state_durations[self.state] += now - self.state_start_time
        self.state_start_time = now
        self.state = new_state

    def publish_stats(self):
        uptime = time.time() - self.start_time
        stats = {
            "uptime_seconds": uptime,
            "current_state": self.state,
            "mode": self.hmi.mode,
            "total_processed": self.total_processed,
            "color_counts": self.color_counts,
            "state_durations": self.state_durations,
            "target_map": self.hmi.target_map,
        }
        self.publish_telemetry(T_STATS, stats)

    # =========================
    # MQTT SETUP
    # =========================
    def setup_mqtt(self):
        self.mqtt.subscribe(C_START, lambda msg: self.handle_start(msg))
        self.mqtt.subscribe(C_STOP, lambda msg: self.handle_stop(msg))
        self.mqtt.subscribe(C_MODE, lambda msg: self.handle_mode(msg))
        self.mqtt.subscribe(C_TARGET, lambda msg: self.handle_target(msg))
        self.mqtt.subscribe(C_MANUAL, lambda msg: self.handle_manual(msg))

        self.mqtt.start()

    def handle_start(self, msg):
        self.hmi.start()
        self.publish_response(R_ACK, {"cmd": "start"})

    def handle_stop(self, msg):
        self.hmi.stop()
        self.publish_response(R_ACK, {"cmd": "stop"})

    def handle_mode(self, msg):
        self.hmi.set_mode(msg)
        self.publish_state(S_MODE, self.hmi.mode)
        self.publish_response(R_ACK, {"cmd": "mode"})

    def handle_target(self, msg):
        self.hmi.set_target(msg)
        self.publish_response(R_ACK, {"cmd": "target"})

    def handle_manual(self, msg):
        parsed = self.hmi.parse_payload(msg)
        if not parsed:
            self.publish_response(R_ERROR, {"msg": "invalid manual payload"})
            return

        color = parsed.get("color")
        target = parsed.get("target")
        if color and target:
            self.hmi.target_map[color] = tuple(target)
            self.publish_response(R_ACK, {"cmd": "manual"})
        else:
            self.publish_response(R_ERROR, {"msg": "manual payload needs color and target"})

    # =========================
    # MQTT PUBLISH HELPERS
    # =========================
    def publish_state(self, topic, value):
        payload = json.dumps({
            "value": value,
            "ts": time.time()
        })
        self.mqtt.publish(topic, payload)

    def publish_telemetry(self, topic, data):
        data["ts"] = time.time()
        self.mqtt.publish(topic, json.dumps(data))

    def publish_response(self, topic, data):
        data["ts"] = time.time()
        self.mqtt.publish(topic, json.dumps(data))

    # =========================
    # MAIN LOOP
    # =========================
    def run(self):
        while True:

            # =========================
            # SYSTEM NOT RUNNING
            # =========================
            if not self.hmi.running:
                self.publish_state(S_SYSTEM, "STOPPED")
                time.sleep(0.1)
                continue

            frame = get_frame()
            if frame is None:
                continue

            # =========================
            # STATE: IDLE
            # =========================
            if self.state == "IDLE":
                self.publish_state(S_SYSTEM, "IDLE")

                objects = self.detector.detect(frame)

                self.publish_telemetry(T_OBJECT, {
                    "count": len(objects),
                    "objects": objects
                })
                self.publish_telemetry(T_CAMERA, {
                    "fps": 0
                })

                for obj in objects:
                    color = obj.get("color")
                    if color in self.color_counts:
                        self.color_counts[color] += 1
                self.total_processed += len(objects)
                self.publish_stats()

                if objects:
                    stop_conveyor()
                    self.publish_state(S_CONVEYOR, "STOP")
                    self.publish_telemetry(T_CONVEYOR, {
                        "status": "STOP",
                        "speed": 0.0
                    })

                    self.last_objects = objects
                    self.enter_state("PROCESS")

            # =========================
            # STATE: PROCESS
            # =========================
            elif self.state == "PROCESS":
                self.publish_state(S_SYSTEM, "PROCESS")
                self.publish_state(S_DOBOT, "BUSY")

                objects = self.detector.detect(frame)

                commands = match_target(objects, self.hmi.target_map)

                for cmd in commands:
                    execute_robot(cmd)
                    self.publish_telemetry(T_DOBOT, {
                        "color": cmd.get("color"),
                        "target_grid": cmd.get("place_grid")
                    })

                self.publish_response(R_DONE, {
                    "status": "completed",
                    "total_cmd": len(commands)
                })

                self.publish_stats()
                self.enter_state("RETURN")

            # =========================
            # STATE: RETURN
            # =========================
            elif self.state == "RETURN":
                self.publish_state(S_SYSTEM, "RETURN")

                start_conveyor()
                self.publish_state(S_CONVEYOR, "RUN")

                self.publish_stats()
                self.enter_state("IDLE")