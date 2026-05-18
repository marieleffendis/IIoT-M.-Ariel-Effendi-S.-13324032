"""
robot/controller.py

Eksekutor gerakan Dobot Magician DT-MG-4R005-02E.
Menggunakan library pydobot (pip install pydobot).

Jika pydobot tidak terinstall, semua perintah akan di-simulate (print saja).
"""

from robot.kinematics import grid_to_world
from config import DOBOT_PORT, DOBOT_Z_PICK, DOBOT_Z_TRAVEL, DOBOT_R

# ============================================================
# INISIALISASI DOBOT (singleton)
# ============================================================
try:
    from pydobot import Dobot as _DobotLib
    _PYDOBOT_AVAILABLE = True
except ImportError:
    _PYDOBOT_AVAILABLE = False
    print("[ROBOT] WARNING: pydobot tidak terinstall → mode simulasi aktif.")
    print("[ROBOT]          Install dengan: pip install pydobot")

_dobot_instance = None


def _get_dobot():
    """Mengembalikan koneksi Dobot (singleton). Buat baru jika belum ada."""
    global _dobot_instance
    if not _PYDOBOT_AVAILABLE:
        return None
    if _dobot_instance is None:
        try:
            _dobot_instance = _DobotLib(port=DOBOT_PORT, verbose=False)
            print(f"[ROBOT] Terhubung ke Dobot di port {DOBOT_PORT}")
        except Exception as e:
            print(f"[ROBOT] ERROR: Gagal konek ke Dobot → {e}")
            _dobot_instance = None
    return _dobot_instance


def disconnect_dobot():
    """Tutup koneksi Dobot (panggil saat shutdown)."""
    global _dobot_instance
    if _dobot_instance:
        _dobot_instance.close()
        _dobot_instance = None
        print("[ROBOT] Koneksi Dobot ditutup.")


# ============================================================
# FUNGSI GERAK DASAR
# ============================================================

def _move(bot, x, y, z, r=DOBOT_R, wait=True):
    """Helper move dengan logging."""
    print(f"[ROBOT]   → move_to({x:.1f}, {y:.1f}, {z:.1f}, r={r})")
    if bot:
        bot.move_to(x, y, z, r, wait=wait)


def _suction(bot, enable: bool):
    """Aktifkan / matikan suction cup."""
    state = "ON" if enable else "OFF"
    print(f"[ROBOT]   → suction {state}")
    if bot:
        bot.suck(enable)


# ============================================================
# API PUBLIK
# ============================================================

def move_to_grid(col, row):
    """
    Gerakkan Dobot ke posisi grid tertentu tanpa pick/place.

    Args:
        col (int): kolom 1..4
        row (int): baris  1..4
    """
    x, y, z, r = grid_to_world(col, row)
    print(f"[ROBOT] MOVE → grid ({col},{row}) = ({x:.1f}, {y:.1f}, {z:.1f})")

    bot = _get_dobot()
    _move(bot, x, y, DOBOT_Z_TRAVEL, r)   # angkat dulu ke ketinggian aman
    _move(bot, x, y, z, r)                 # turun ke posisi grid


def execute_robot(cmd):
    """
    Eksekusi satu perintah pick-and-place.

    Format cmd:
        {
            "pick_pixel" : (cx, cy),   # koordinat pixel objek di frame 4K (None = skip pick)
            "place_grid" : (col, row), # posisi grid tujuan, 1-indexed
            "color"      : "red",      # informasi warna (untuk logging/MQTT)
        }

    Alur gerak:
        1. Angkat ke DOBOT_Z_TRAVEL
        2. Gerak ke posisi pick (pixel → world konversi via kalibrasi)
        3. Turun ke DOBOT_Z_PICK, suction ON
        4. Angkat ke DOBOT_Z_TRAVEL
        5. Gerak ke posisi place (grid → world)
        6. Turun ke DOBOT_Z_PLACE, suction OFF
        7. Angkat ke DOBOT_Z_TRAVEL (home safe)

    Catatan:
        Konversi pick_pixel → world memerlukan kalibrasi homografi
        antara kamera 4K dan ruang Dobot. Implementasikan fungsi
        pixel_to_world() di robot/calibration.py lalu sambungkan di sini.
    """
    col, row = cmd["place_grid"]
    color    = cmd.get("color", "unknown")
    x_place, y_place, z_place, r = grid_to_world(col, row)

    print(f"[ROBOT] CMD: color={color} | place=({col},{row})")

    bot = _get_dobot()

    # --- Step 1: Angkat ke ketinggian aman ---
    _move(bot, x_place, y_place, DOBOT_Z_TRAVEL, r)

    # --- Step 2–4: PICK ---
    if cmd.get("pick_pixel") is not None:
        px, py = cmd["pick_pixel"]
        print(f"[ROBOT] PICK at pixel ({px}, {py})")

        # TODO: Ganti dengan pixel_to_world(px, py) setelah kalibrasi
        # Sementara: posisi pick di atas conveyor di-hardcode
        # from robot.calibration import pixel_to_world
        # wx, wy = pixel_to_world(px, py)
        wx, wy = px, py   # PLACEHOLDER — ganti setelah kalibrasi
        print(f"[ROBOT]   pick world (estimasi): ({wx}, {wy})")

        _move(bot, wx, wy, DOBOT_Z_TRAVEL, r)
        _move(bot, wx, wy, DOBOT_Z_PICK, r)
        _suction(bot, True)
        _move(bot, wx, wy, DOBOT_Z_TRAVEL, r)
    else:
        print("[ROBOT] PICK dilewati (tidak ada pick_pixel)")

    # --- Step 5–7: PLACE ---
    print(f"[ROBOT] PLACE at ({x_place:.1f}, {y_place:.1f}, {z_place:.1f})")
    _move(bot, x_place, y_place, DOBOT_Z_TRAVEL, r)
    _move(bot, x_place, y_place, z_place, r)
    _suction(bot, False)
    _move(bot, x_place, y_place, DOBOT_Z_TRAVEL, r)

    print(f"[ROBOT] SELESAI: {color} → grid ({col},{row})")