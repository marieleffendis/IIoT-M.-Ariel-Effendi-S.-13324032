import json
import ast

class HMIHandler:
    def __init__(self):
        self.mode = "AUTO"
        self.target_map = {}
        self.running = False

    def set_mode(self, mode):
        print("[HMI] Mode:", mode)
        self.mode = mode

    def parse_payload(self, payload):
        if isinstance(payload, dict):
            return payload
        try:
            return json.loads(payload)
        except Exception:
            try:
                return ast.literal_eval(payload)
            except Exception:
                return None

    def set_target(self, target):
        parsed = self.parse_payload(target)
        if parsed is None:
            print("[HMI] Invalid target payload")
            return
        print("[HMI] Target updated")
        self.target_map = parsed

    def start(self):
        print("[HMI] START")
        self.running = True

    def stop(self):
        print("[HMI] STOP")
        self.running = False