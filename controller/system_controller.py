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

    def setup_mqtt(self):
        self.mqtt.subscribe(CMD_START, lambda msg: self.hmi.start())
        self.mqtt.subscribe(CMD_STOP, lambda msg: self.hmi.stop())
        self.mqtt.subscribe(CMD_MODE, lambda msg: self.hmi.set_mode(msg))

        self.mqtt.start()

    def run(self):
        while True:
            if not self.hmi.running:
                continue

            frame = get_frame()
            if frame is None:
                continue

            if self.state == "IDLE":
                objs = self.detector.detect(frame)

                if objs:
                    stop_conveyor()
                    self.state = "PROCESS"

            elif self.state == "PROCESS":
                objs = self.detector.detect(frame)

                commands = match_target(objs, self.hmi.target_map)

                for cmd in commands:
                    execute_robot(cmd)

                self.state = "RETURN"

            elif self.state == "RETURN":
                start_conveyor()
                self.state = "IDLE"