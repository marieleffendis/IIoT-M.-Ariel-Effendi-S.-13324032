import cv2
import numpy as np
import time
import json
import threading
from datetime import datetime
from serial.tools import list_ports
from pydobotplus import Dobot
import paho.mqtt.client as mqtt

# ── Local modules ──────────────────────────────────────────────────────────────
import utility2
from config import MODEL_PATH, CAMERA_INDEX, CONVEYOR_SPEED, CONVEYOR_DELAY, MQTT_BROKER, MQTT_TOPIC
from vision.hybrid_detector import HybridDetector
from logic.matcher import match_target
from logic.state_machine import StateMachine
from robot.controller import execute_robot


# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURASI FALLBACK (jika config.py tidak memiliki nilai ini)
# ══════════════════════════════════════════════════════════════════════════════
try:
    from config import (
        MODEL_PATH, CAMERA_INDEX, CONVEYOR_SPEED,
        CONVEYOR_DELAY, MQTT_BROKER, MQTT_TOPIC
    )
except ImportError:
    MODEL_PATH     = "model.pt"
    CAMERA_INDEX   = 0
    CONVEYOR_SPEED = 1
    CONVEYOR_DELAY = 1.16
    MQTT_BROKER    = "localhost"
    MQTT_TOPIC     = "dobot/telemetry"

# Target zona per warna (koordinat robot, sesuaikan kebutuhan)
TARGET_MAP = {
    "red":    (0, 0),
    "green":  (1, 1),
    "blue":   (2, 2),
    "yellow": (3, 3),
}

# ROI — disesuaikan dari kode lama
ROI_Y_START, ROI_Y_END = 71,  164
ROI_X_START, ROI_X_END = 145, 263


# ══════════════════════════════════════════════════════════════════════════════
# HARDWARE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def init_dobot() -> Dobot | None:
    """Cari port serial dan sambungkan ke Dobot."""
    ports = list_ports.comports()
    if len(ports) < 2:
        print("[ERROR] Port serial tidak cukup (butuh index 1).")
        return None
    port = ports[1].device
    print(f"[INFO] Menghubungkan Dobot di {port} ...")
    try:
        device = Dobot(port=port)
        print("[INFO] Dobot terhubung.")
        return device
    except Exception as exc:
        print(f"[ERROR] Gagal koneksi Dobot: {exc}")
        return None


def save_history(color_name: str, pose) -> None:
    """Tulis log pickup ke history.txt."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    x, y, z = pose[0][0], pose[0][1], pose[0][2]
    entry = f"[{timestamp}] Warna: {color_name} | Posisi: X:{x:.2f} Y:{y:.2f} Z:{z:.2f}\n"
    try:
        with open("history.txt", "a") as f:
            f.write(entry)
        print(f"[LOG] Tersimpan → {entry.strip()}")
    except Exception as exc:
        print(f"[ERROR] Gagal simpan history: {exc}")


def clear_camera_buffer(cap: cv2.VideoCapture, n: int = 5) -> None:
    for _ in range(n):
        cap.read()


# ══════════════════════════════════════════════════════════════════════════════
# TELEMETRY THREAD
# ══════════════════════════════════════════════════════════════════════════════

_system_status = "IDLE"
_status_lock   = threading.Lock()


def set_status(status: str) -> None:
    global _system_status
    with _status_lock:
        _system_status = status


def get_status() -> str:
    with _status_lock:
        return _system_status


def telemetry_worker(device: Dobot, client: mqtt.Client,
                     topic: str, dobot_lock: threading.Lock) -> None:
    """Publish posisi + status ke MQTT setiap 0.5 detik."""
    print("📡 Thread Telemetri aktif.")
    while True:
        try:
            with dobot_lock:
                pos = device.get_pose()
            x, y, z, r = pos[0]
            payload = {
                "telemetry": {
                    "x": round(float(x), 2),
                    "y": round(float(y), 2),
                    "z": round(float(z), 2),
                    "r": round(float(r), 2),
                },
                "status": get_status(),
            }
            client.publish(topic, json.dumps(payload))
        except Exception as exc:
            print(f"⚠️  Telemetry error: {exc}")
        time.sleep(0.5)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── Hardware init ──────────────────────────────────────────────────────
    device = init_dobot()
    if device is None:
        return

    dobot_lock = threading.Lock()

    # ── MQTT ───────────────────────────────────────────────────────────────
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()

    threading.Thread(
        target=telemetry_worker,
        args=(device, client, MQTT_TOPIC, dobot_lock),
        daemon=True,
    ).start()

    # ── Vision + State ─────────────────────────────────────────────────────
    detector = HybridDetector(MODEL_PATH)
    sm       = StateMachine()         # state awal: "IDLE"

    # ── Kamera ────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # ── Mulai Conveyor ─────────────────────────────────────────────────────
    print(f"[CONVEYOR] Berjalan (speed={CONVEYOR_SPEED}) ...")
    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
    set_status("IDLE")

    detected_color: str = ""

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Gagal baca frame.")
                break

            # ── Deteksi via HybridDetector ─────────────────────────────
            roi    = frame[ROI_Y_START:ROI_Y_END, ROI_X_START:ROI_X_END]
            objects = detector.detect(roi)           # returns list[dict]

            # Overlay ROI box
            cv2.rectangle(frame,
                          (ROI_X_START, ROI_Y_START),
                          (ROI_X_END,   ROI_Y_END),
                          (255, 255, 255), 2)

            # Overlay bounding box deteksi
            for obj in objects:
                # HybridDetector diharapkan mengembalikan:
                # {"label": str, "bbox": (x,y,w,h), "color": (B,G,R)}
                label = obj.get("label", "?")
                bbox  = obj.get("bbox")
                color = obj.get("color", (0, 255, 0))
                if bbox:
                    ox, oy, ow, oh = bbox
                    gx, gy = ox + ROI_X_START, oy + ROI_Y_START
                    cv2.rectangle(frame, (gx, gy), (gx+ow, gy+oh), color, 2)
                    cv2.putText(frame, label, (gx, gy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.imshow("Integrated System", frame)

            # ── State Machine ──────────────────────────────────────────
            state = sm.get()

            # ------------------------------------------------------------------
            if state == "IDLE":
                set_status("IDLE — Scanning")
                if objects:
                    detected_color = objects[0].get("label", "unknown")
                    print(f"[DETEKSI] {detected_color} ditemukan → WAITING_ARRIVAL")
                    set_status(f"Waiting Arrival: {detected_color}")
                    sm.set("WAITING_ARRIVAL")

            # ------------------------------------------------------------------
            elif state == "WAITING_ARRIVAL":
                # Beri waktu objek berjalan ke pick-point
                print(f"[CONVEYOR] Menunggu {CONVEYOR_DELAY}s ...")
                cv2.waitKey(1)
                time.sleep(CONVEYOR_DELAY)

                print("[CONVEYOR] STOP.")
                device.conveyor_belt(speed=0, direction=1)
                sm.set("PROCESS")

            # ------------------------------------------------------------------
            elif state == "PROCESS":
                set_status(f"Processing: {detected_color}")

                # Re-deteksi setelah conveyor berhenti
                ret2, frame2 = cap.read()
                if ret2:
                    clear_camera_buffer(cap)
                    roi2    = frame2[ROI_Y_START:ROI_Y_END, ROI_X_START:ROI_X_END]
                    objects = detector.detect(roi2)

                if not objects:
                    print("[WARN] Objek hilang dari ROI, kembali IDLE.")
                    sm.set("IDLE")
                    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
                    continue

                # Terjemahkan deteksi → perintah robot
                commands = match_target(objects, TARGET_MAP)

                with dobot_lock:
                    set_status("Executing Robot Movement")
                    try:
                        # --- Gerakan via modular execute_robot ---
                        for cmd in commands:
                            execute_robot(cmd)

                        # --- Fallback posisiA (dari utility2) jika perlu ---
                        # utility2.posisiA(device)

                        # Simpan history
                        pose = device.get_pose()
                        save_history(detected_color, pose)

                    except Exception as exc:
                        print(f"[ERROR] Gerakan robot gagal: {exc}")

                    # Publish history ke MQTT
                    history_payload = {
                        "history_item": {
                            "id":     int(time.time()),
                            "color":  detected_color,
                            "target": commands[0].get("zone", "?") if commands else "?",
                            "time":   datetime.now().strftime("%H:%M"),
                        }
                    }
                    client.publish("dobot/history", json.dumps(history_payload))

                sm.set("RETURN")

            # ------------------------------------------------------------------
            elif state == "RETURN":
                set_status("Returning — Restart Conveyor")
                print("[CONVEYOR] Mulai lagi.")
                device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
                detected_color = ""
                sm.set("IDLE")

            # ── Tombol quit ────────────────────────────────────────────
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Keluar manual (q).")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh user (Ctrl+C).")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if device:
            device.conveyor_belt(speed=0, direction=1)
            device.close()
        client.loop_stop()
        print("[INFO] Semua resource dibebaskan. Program selesai.")


if __name__ == "__main__":
    main()