class StateMachine:
    def __init__(self):
        self.state = "IDLE"

    def set(self, new_state):
        print(f"[STATE] {self.state} → {new_state}")
        self.state = new_state

    def get(self):
        return self.state