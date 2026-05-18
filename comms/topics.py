# ============================================================
# comms/topics.py
# Daftar topik MQTT lengkap untuk sistem IIoT Dobot
# Format: IIoT/Labtek_VI/Lab_TF_C/docon_01/<Category>/<SubTopic>
# ============================================================

BASE = "IIoT/Labtek_VI/Lab_TF_C/docon_01"

# --- TELEMETRY ---
T_CAMERA    = f"{BASE}/Telemetry/camera"      # payload: {"fps": 60}
T_OBJECT    = f"{BASE}/Telemetry/object"      # payload: {"count": 2, "objects": [...]}
T_DOBOT     = f"{BASE}/Telemetry/dobot"       # payload: {"x": 120, "y": 200}
T_CONVEYOR  = f"{BASE}/Telemetry/conveyor"    # payload: {"speed": 1.0}
T_STATS     = f"{BASE}/Telemetry/stats"       # payload: ringkasan statistik sistem

# --- STATE ---
S_SYSTEM    = f"{BASE}/State/system"          # IDLE / PROCESS / RETURN
S_MODE      = f"{BASE}/State/mode"            # AUTO / MANUAL
S_CONVEYOR  = f"{BASE}/State/conveyor"        # RUN / STOP
S_DOBOT     = f"{BASE}/State/dobot"           # BUSY / READY

# --- COMMAND ---
C_START     = f"{BASE}/Command/start"         # payload: {}
C_STOP      = f"{BASE}/Command/stop"          # payload: {}
C_MODE      = f"{BASE}/Command/mode"          # payload: "AUTO" atau "MANUAL"
C_TARGET    = f"{BASE}/Command/target"        # payload: {"red": [0,1], ...}
C_MANUAL    = f"{BASE}/Command/manual"        # payload: {"color":"red","target":[2,2]}

# --- RESPONSE ---
R_DONE      = f"{BASE}/Response/done"         # payload: {"status": "completed"}
R_ERROR     = f"{BASE}/Response/error"        # payload: {"msg": "fail defect"}
R_ACK       = f"{BASE}/Response/ack"          # payload: {"cmd": "start"}