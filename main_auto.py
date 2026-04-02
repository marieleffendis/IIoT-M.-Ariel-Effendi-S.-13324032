import cv2
import numpy as np
import time
import sys
from serial.tools import list_ports
from pydobotplus import Dobot
import utility2
from datetime import datetime

# ==========================================
# KONFIGURASI KAMERA & CONVEYOR
# ==========================================
CAMERA_INDEX = 0
CONVEYOR_SPEED = 1
# Disamakan dengan Mode 1 (posA.py)
CONVEYOR_DELAY = 1.25 

# ROI (Region of Interest) - Disamakan persis dengan Mode 1
ROI_Y_START, ROI_Y_END = 71, 164
ROI_X_START, ROI_X_END = 145, 263

# ==========================================
# DATABASE WARNA (PERSIS SEPERTI MODE 1)
# ==========================================
# Menggunakan konfigurasi yang sama persis dengan posA.py
# agar pembacaan kamera dan delay-nya konsisten.
COLORS_CONFIG = {
    "Merah": { "lower": np.array([0, 120, 70]), "upper": np.array([10, 255, 255]), "box_color": (0, 0, 255) },
    "Merah (Alt)": { "lower": np.array([170, 120, 70]), "upper": np.array([180, 255, 255]), "box_color": (0, 0, 255) },
    "Hijau": { "lower": np.array([36, 50, 50]), "upper": np.array([86, 255, 255]), "box_color": (0, 255, 0) },
    "Biru":  { "lower": np.array([100, 50, 50]), "upper": np.array([130, 255, 255]), "box_color": (255, 0, 0) },
    "Kuning":{ "lower": np.array([20, 100, 100]), "upper": np.array([35, 255, 255]), "box_color": (0, 255, 255) }
}

# ==========================================
# FUNGSI PENDUKUNG
# ==========================================
def init_dobot():
    available_ports = list_ports.comports()
    if not available_ports:
        return None
    try:
        # Asumsi port Dobot ada di index 1
        device = Dobot(port=available_ports[1].device)
        return device
    except:
        return None

def clear_camera_buffer(cap):
    # Buang frame lama agar tidak delay
    for _ in range(5):
        cap.read()

def get_mask_for_color(hsv_frame, color_name):
    """Helper untuk mendapatkan mask sesuai nama warna dari config Mode 1"""
    # Jika Merah, kita harus cek "Merah" DAN "Merah (Alt)"
    if color_name == "Merah":
        params1 = COLORS_CONFIG["Merah"]
        mask1 = cv2.inRange(hsv_frame, params1["lower"], params1["upper"])
        
        params2 = COLORS_CONFIG["Merah (Alt)"]
        mask2 = cv2.inRange(hsv_frame, params2["lower"], params2["upper"])
        
        return mask1 | mask2, params1["box_color"]
    else:
        # Untuk warna lain (Hijau, Biru, Kuning)
        if color_name in COLORS_CONFIG:
            params = COLORS_CONFIG[color_name]
            mask = cv2.inRange(hsv_frame, params["lower"], params["upper"])
            return mask, params["box_color"]
    return None, (255,255,255)

# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    # 1. BACA ARGUMEN DARI GUI
    if len(sys.argv) < 5:
        print("[ERROR] Argumen warna kurang! Jalankan via GUI.")
        return

    # Mapping Tugas: Posisi -> Warna Target
    task_list = {
        "A": sys.argv[1],
        "B": sys.argv[2],
        "C": sys.argv[3],
        "D": sys.argv[4]
    }
    
    # Status: False = Belum Selesai, True = Selesai
    task_status = {"A": False, "B": False, "C": False, "D": False}

    print(f"=== MEMULAI MISI ===")
    for pos, color in task_list.items():
        print(f"Posisi {pos} -> Menunggu: {color}")
    print("====================")

    # 2. INISIALISASI HARDWARE
    device = init_dobot()
    if device is None:
        print("[ERROR] Dobot tidak ditemukan.")
        return

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Start Conveyor
    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
    
    try:
        while True:
            # Cek Kemenangan (Semua tugas selesai)
            if all(task_status.values()):
                print("\n[INFO] SEMUA POSISI TERISI! MISI SELESAI.")
                break

            ret, frame = cap.read()
            if not ret: break

            # --- PRE-PROCESSING GAMBAR (Disamakan Mode 1) ---
            roi = frame[ROI_Y_START:ROI_Y_END, ROI_X_START:ROI_X_END]
            # Gaussian Blur kernel (11, 11) sama seperti posA.py
            blurred_roi = cv2.GaussianBlur(roi, (11, 11), 0)
            hsv_roi = cv2.cvtColor(blurred_roi, cv2.COLOR_BGR2HSV)

            detected_pos = None     
            detected_color = None
            detected_box_color = (0, 0, 0)

            # --- LOOP PENGECEKAN TUGAS ---
            # Cek setiap tugas yang belum selesai
            for pos, target_color in task_list.items():
                if task_status[pos]: 
                    continue # Skip jika posisi ini sudah beres

                # Ambil Mask menggunakan settingan Mode 1
                mask, box_col = get_mask_for_color(hsv_roi, target_color)
                
                if mask is not None:
                    # Erode & Dilate (Sama seperti Mode 1)
                    mask = cv2.erode(mask, None, iterations=2)
                    mask = cv2.dilate(mask, None, iterations=2)
                    
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    if len(contours) > 0:
                        c = max(contours, key=cv2.contourArea)
                        x, y, w, h = cv2.boundingRect(c)
                        
                        # Filter ukuran objek (> 10 pixel sama seperti Mode 1)
                        if w > 10 and h > 10:
                            detected_pos = pos
                            detected_color = target_color
                            detected_box_color = box_col
                            
                            # Visualisasi di layar
                            gx, gy = x + ROI_X_START, y + ROI_Y_START
                            cv2.rectangle(frame, (gx, gy), (gx+w, gy+h), detected_box_color, 2)
                            cv2.putText(frame, f"{target_color}->{pos}", (gx, gy-5), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, detected_box_color, 2)
                            
                            # Break agar prioritas urutan (A->B->C->D) terjaga dan tidak double detect
                            break 
            
            # --- UI DASHBOARD ---
            cv2.rectangle(frame, (ROI_X_START, ROI_Y_START), (ROI_X_END, ROI_Y_END), (255, 255, 255), 2)
            cv2.imshow("Monitoring Sistem", frame)

            # --- EKSEKUSI ROBOT ---
            if detected_pos:
                print(f"[DETEKSI] Ditemukan {detected_color} untuk Posisi {detected_pos}!")
                
                # 1. Delay (Persis Mode 1)
                print(f" >> Menunggu {CONVEYOR_DELAY} detik agar objek sampai...")
                cv2.waitKey(1)
                time.sleep(CONVEYOR_DELAY)
                
                # 2. Stop Conveyor
                print(" >> STOP Conveyor.")
                device.conveyor_belt(speed=0, direction=1)
                
                # 3. Gerakkan Robot
                print(f" >> Bergerak ke Posisi {detected_pos}...")
                try:
                    if detected_pos == "A":
                        utility2.posisiA(device)
                    elif detected_pos == "B":
                        utility2.posisiB(device)
                    elif detected_pos == "C":
                        utility2.posisiC(device)
                    elif detected_pos == "D":
                        utility2.posisiD(device)
                    
                    # Tandai tugas selesai
                    task_status[detected_pos] = True
                    print(f" >> Posisi {detected_pos} Selesai.")

                except Exception as e:
                    print(f"[ERROR] Gerak Robot Gagal: {e}")

                # 4. Lanjut Conveyor (Jika misi belum selesai total)
                if not all(task_status.values()):
                    print(" >> Lanjut Conveyor...")
                    device.conveyor_belt(speed=CONVEYOR_SPEED, direction=1)
                    clear_camera_buffer(cap)
                
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Stop manual user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if device:
            device.conveyor_belt(speed=0, direction=1)
            device.close()

if __name__ == "__main__":
    main()
