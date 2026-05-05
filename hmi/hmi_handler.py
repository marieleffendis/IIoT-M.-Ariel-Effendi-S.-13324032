class HMIHandler:
    def __init__(self):
        self.mode = "AUTO"
        self.target_map = {}
        self.running = False

    def set_mode(self, mode):
        print("[HMI] Mode:", mode)
        self.mode = mode

    def set_target(self, target):
        print("[HMI] Target updated")
        self.target_map = target

    def start(self):
        print("[HMI] START")
        self.running = True

    def stop(self):
        print("[HMI] STOP")
        self.running = False