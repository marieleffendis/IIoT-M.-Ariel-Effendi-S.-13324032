# ============================================================
# CONFIG - IIoT Dobot Magician System
# ============================================================

# --- Model ---
MODEL_PATH = "models/best.pt"

# --- Grid ---
GRID_SIZE = 4
CELL_SIZE_MM = 20           # Lebar/panjang 1 sel grid = 20 mm

# --- Koordinat Dobot (1-indexed: col, row) ---
# Titik asal = posisi grid (1,1) = sudut kiri atas papan
# x berkurang seiring col bertambah (kiri → kanan)
# y bertambah seiring row bertambah (atas → bawah)
DOBOT_ORIGIN_X   = 49      # x saat col=1
DOBOT_ORIGIN_Y   = 200     # y saat row=1
DOBOT_Z_PLACE    = -35.0   # z saat meletakkan blok
DOBOT_Z_PICK     = -55.0   # z saat mengambil blok dari conveyor (estimasi, kalibrasi ulang)
DOBOT_Z_TRAVEL   = 20.0    # z aman saat perpindahan
DOBOT_R          = 19      # rotasi claw (tetap)

# --- Koneksi Dobot ---
DOBOT_PORT = "COM3"        # Sesuaikan dengan port aktual (Windows: COM3/COM4, Linux: /dev/ttyUSB0)

# --- Kamera ---
CAMERA_INDEX  = 0
CAMERA_WIDTH  = 3840       # 4K UHD
CAMERA_HEIGHT = 2160

# --- ROI Detection Zone (koordinat pixel pada frame 4K) ---
# Area persegi panjang di atas conveyor tempat objek dikenali.
# Kalibrasi: titik tengah ROI = titik tengah lebar conveyor.
# Ubah nilai ini sesuai posisi kamera dan conveyor aktual.
ROI_X1 = 1600
ROI_Y1 = 800
ROI_X2 = 2240
ROI_Y2 = 1360

# --- Perspective Warp (untuk target_parser gambar 4x4) ---
WARP_SIZE = 400