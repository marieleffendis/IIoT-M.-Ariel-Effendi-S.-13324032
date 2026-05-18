import argparse
import json
import cv2

from vision.target_parser import parse_target
from hardware.camera import get_frame
from robot.controller import execute_robot
from logic.matcher import match_target


def load_target_map(map_string):
    if not map_string:
        return {
            "red": (0, 0),
            "green": (0, 1),
            "blue": (0, 2),
            "yellow": (0, 3)
        }

    try:
        data = json.loads(map_string)
        return {color: tuple(pos) for color, pos in data.items()}
    except json.JSONDecodeError:
        print("[AUTO] Gagal mem-parsing target map. Gunakan JSON valid seperti '{\"red\":[0,0],\"green\":[0,1]}'")
        raise


def capture_layout(image_path=None):
    if image_path:
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        return image

    frame = get_frame()
    if frame is None:
        raise RuntimeError("Gagal menangkap frame dari kamera")

    return frame


def build_commands_from_layout(layout, target_map):
    commands = []
    for color, grid_pos in layout.items():
        if color not in target_map:
            continue
        commands.append({
            "place_grid": target_map[color],
            "pick_pixel": None,
            "source_grid": grid_pos,
            "color": color
        })
    return commands


def main():
    parser = argparse.ArgumentParser(description="Auto mode untuk sistem Dobot 4x4")
    parser.add_argument("--image", help="Path ke gambar layout 4x4 untuk dikenali")
    parser.add_argument("--target-map", help="JSON string dari peta target warna", default=None)
    args = parser.parse_args()

    print("[AUTO] Memulai mode otomatis")
    target_map = load_target_map(args.target_map)

    image = capture_layout(args.image)
    layout = parse_target(image)

    if not layout:
        print("[AUTO] Tidak ada blok warna yang terdeteksi pada layout")
        return

    print(f"[AUTO] Detected layout: {layout}")
    print(f"[AUTO] Target mapping: {target_map}")

    commands = build_commands_from_layout(layout, target_map)
    if not commands:
        print("[AUTO] Tidak ada perintah robot yang dibuat karena mapping tidak cocok")
        return

    for cmd in commands:
        print(f"[AUTO] Mengirim perintah: {cmd}")
        execute_robot(cmd)

    print("[AUTO] Selesai menjalankan perintah otomatis")


if __name__ == "__main__":
    main()
