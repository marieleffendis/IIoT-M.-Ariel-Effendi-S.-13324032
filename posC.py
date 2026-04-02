import cv2
import numpy as np
import time
from serial.tools import list_ports
from pydobotplus import Dobot
import utility2
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import threading

dobot_lock = threading.Lock()
system_status = "Scanning Mode 1"

# ==========================================
# KONFIGURASI
# ==========================================
CAMERA_INDEX = 0           # Ganti 0 atau 1 sesuai kamera
CONVEYOR_SPEED = 1         # Sesuai file conveyor_test.py
CONVEYOR_DELAY = 1.25       # Waktu tunggu setelah deteksi sebelum conveyor stop
MQTT_BROKER = "localhost"
MQTT_TOPIC = "dobot/telemetry"


# Database Warna (Sesuai camera.py)
COLORS_CONFIG = {
    "Merah": { "lower": np.array([0, 120, 70]), "upper": np.array([10, 255, 255]), "box_color": (0, 0, 255) },
    "Merah (Alt)": { "lower": np.array([170, 120, 70]), "upper": np.array([180, 255, 255]), "box_color": (0, 0, 255) },
    "Hijau": { "lower": np.array([36, 50, 50]), "upper": np.array([86, 255, 255]), "box_color": (0, 255, 0) },
    "Biru":  { "lower": np.array([100, 50, 50]), "upper": np.array([130, 255, 255]), "box_color": (255, 0, 0) },
    "Kuning":{ "lower": np.array([20, 100, 100]), "upper": np.array([35, 255, 255]), "box_color": (0, 255, 255) }
}

# ROI (Region of Interest) - Sesuai camera.py
ROI_Y_START, ROI_Y_END = 71, 164
ROI_X_START, ROI_X_END = 145, 263

# ==========================================
# FUNGSI PENDUKUNG
# ==========================================

def init_dobot():
    """Mencari port dan menghubungkan ke Dobot"""
    available_ports = list_ports.comports()
    if not available_ports:
        print("[ERROR] Tidak ada port serial yang ditemukan.")
        return None
    
    # Mengambil port pertama sesuai logika main2.py
    port = available_ports[1].device
    print(f"[INFO] Mencoba terhubung ke Dobot di port: {port}...")
    
    try:
        device = Dobot(port=port)
        print("[INFO] Dobot terhubung berhasil.")
        return device
    except Exception as e:
        print(f"[ERROR] Gagal connect ke Dobot: {e}")
        return None

def save_history(color_name, pose):
    """Menyimpan data ke history.txt"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Format pose [x, y, z, r]
    pose_str = f"X:{pose[0]:.2f}, Y:{pose[1]:.2f}, Z:{pose[2]:.2f}"
    
    log_entry = f"[{timestamp}] Deteksi: {color_name} | Posisi Akhir: {pose_str}\n"
    
    try:
        with open("history.txt", "a") as f:
            f.write(log_entry)
        print(f"[LOG] Data tersimpan di history.txt")
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan history: {e}")

def clear_camera_buffer(cap):
    """Membersihkan buffer kamera agar tidak memproses frame lama"""
    for _ in range(5):
        cap.read()

def telemetry_worker(device, client, topic):
    """Fungsi khusus untuk mengirim data telemetri secara kontinu"""
    print("📡 Thread Telemetri Aktif...")
    global system_status
    while True:
        try:
            # Gunakan lock agar tidak tabrakan dengan gerakan robot
            with dobot_lock:
                pos = device.get_pose()
                x, y, z, r = pos[0]
            
            payload = {
                "telemetry": {
                    "x": round(float(x), 2),
                    "y": round(float(y), 2),
                    "z": round(float(z), 2),
                    "r": round(float(r), 2)
                },
                "status": system_status
            }
            client.publish(topic, json.dumps(payload))
            
        except Exception as e:
            print(f"⚠️ Telemetry Error: {e}")
        
        # Kirim setiap 0.5 detik (bisa disesuaikan)
        time.sleep(0.5)

# ==========================================
# MAIN PROGRAM
# ==========================================

def main():
    global system_status
    # 1. Inisialisasi Dobot
    device = init_dobot()
    if device is None:
        return
    
    # set up mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()

    #init thread
    t = threading.Thread(target=telemetry_worker, args=(device, client, MQTT_TOPIC), daemon=True)
    t.start()

    # 2. Inisialisasi Kamera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 3. NYALAKAN CONVEYOR DI AWAL
    print(f"[CONVEYOR] Start berjalan (Speed: {CONVEYOR_SPEED})...")
    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)

    print(f"Sistem Siap. Menunggu objek di area ROI...")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Gagal membaca frame kamera.")
                break

            # --- PROSES DETEKSI GAMBAR ---
            roi = frame[ROI_Y_START:ROI_Y_END, ROI_X_START:ROI_X_END]
            blurred_roi = cv2.GaussianBlur(roi, (11, 11), 0)
            hsv_roi = cv2.cvtColor(blurred_roi, cv2.COLOR_BGR2HSV)

            object_detected = False
            detected_color_name = ""

            for color_name, params in COLORS_CONFIG.items():
                mask = cv2.inRange(hsv_roi, params["lower"], params["upper"])
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)
                
                contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if len(contours) > 0:
                    c = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(c)

                    if w > 10 and h > 10:
                        # Visualisasi kotak
                        global_x, global_y = x + ROI_X_START, y + ROI_Y_START
                        cv2.rectangle(frame, (global_x, global_y), (global_x+w, global_y+h), params["box_color"], 2)
                        cv2.putText(frame, color_name, (global_x, global_y-5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, params["box_color"], 2)
                        
                        object_detected = True
                        detected_color_name = color_name
                        break # Deteksi satu warna saja

            global system_status
            if object_detected:
                system_status = f"Detecting {detected_color_name}"
            else:
                system_status = "Scanning Mode 1"

            # Tampilkan ROI Area
            cv2.rectangle(frame, (ROI_X_START, ROI_Y_START), (ROI_X_END, ROI_Y_END), (255, 255, 255), 2)
            cv2.imshow("Sistem Integrasi", frame)

            # --- LOGIKA KONTROL UTAMA ---
            if object_detected:
                print(f"[DETEKSI] Objek {detected_color_name} ditemukan!")
                system_status = "Waiting for Arrival"

                # 1. Tunggu (delay agar objek sampai)
                print(f" >> Menunggu {CONVEYOR_DELAY} detik agar objek sampai...")
                cv2.waitKey(1) 
                time.sleep(CONVEYOR_DELAY)

                # 2. Hentikan Conveyor
                print(" >> STOP Conveyor.")
                device.conveyor_belt(speed=0, direction=1)

                # 3. Jalankan Robot Sequence
                with dobot_lock:
                    system_status = "Executing Movement"
                    print(" >> Menjalankan Robot Arm (Posisi A)...")
                    try:
                        # HANYA MENJALANKAN POSISI A (Sesuai request tanpa B,C,D)
                        utility2.posisiC(device)
                        
                        # Simpan data posisi terakhir & warna
                        current_pose = device.get_pose()
                        save_history(detected_color_name, current_pose)
                        print(" >> Robot selesai bergerak dan data tersimpan.")

                    except Exception as e:
                        print(f"[ERROR] Robot movement error: {e}")

                    # kirim ke mqtt
                    history_payload = {
                        "history_item": {
                            "id": int(time.time()),
                            "color": detected_color_name,
                            "target": "Zone A",
                            "time": datetime.now().strftime("%H:%M")
                        }
                    }
                    client.publish("dobot/history", json.dumps(history_payload))
                    
                    # 4. KELUAR DARI PROGRAM SETELAH SATU TUGAS SELESAI
                    print(" >> Tugas selesai. Keluar dari program.")
                    system_status = "Scanning Mode 1" 
                    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
                    break # <- Break ini akan menghentikan loop while True setelah tugas selesai

            # Tombol Keluar 'q' (Manual exit)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("Program dihentikan user.")
    
    finally:
        # Cleanup (Akan tereksekusi otomatis setelah 'break')
        cap.release()
        cv2.destroyAllWindows()
        # Matikan conveyor dan putus koneksi robot
        if device:
            device.conveyor_belt(speed=0, direction=1) # Pastikan conveyor mati total
            device.close()
        print("Program Selesai (Exit).")

if __name__ == "__main__":
    main()
