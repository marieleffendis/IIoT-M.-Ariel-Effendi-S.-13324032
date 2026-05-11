from pydobotplus import Dobot, CustomPosition
from time import sleep

# ================== POSISI ==================

def get_posisi_awal():
    return CustomPosition(173.8, 3.45, 57.44, 20.7)

def get_posisi_awal_bg():
    return CustomPosition(171, -42, 55, 6)

def get_predropzone_posA():
    return CustomPosition(32.5, 199.5, -14.5, 100)

def get_predropzone_posB():
    return CustomPosition(-23.2, 200.6, -14.5, 100)

def get_predropzone_posD():
    return CustomPosition(-22.5, 247, -14.5, 100)

def get_predropzone_posC():
    return CustomPosition(27, 243, -14.5, 100)

# ================== GERAK DASAR ==================

def ke_posisi_awal(device: Dobot):
    pos = get_posisi_awal()
    device.move_to(pos.x, pos.y, pos.z, pos.r, wait=True)

def ke_posisi_awal_bg(device: Dobot):
    pos = get_posisi_awal_bg()
    device.move_to(pos.x, pos.y, pos.z, pos.r, wait=True)

# ================== AKSI ==================

def pick_payload(device: Dobot, position: CustomPosition):
    print("Pick payload")
    ke_posisi_awal(device)
    sleep(1)

    device.move_to(position.x, position.y, position.z - 40, position.r, wait=True)
    sleep(1)

    device.grip(enable=False)   # GRIP ON
    sleep(1)
    ke_posisi_awal(device)

def place_payload(device: Dobot, position: CustomPosition):
    print("Place payload")
    device.move_to(position.x, position.y, position.z + 90, position.r, wait=True)
    sleep(1)

    device.move_to(position.x, position.y, position.z, position.r, wait=True)
    sleep(1)

    device.grip(enable=True)  # GRIP OFF
    sleep(1)

    device.move_to(position.x, position.y, position.z + 120, position.r, wait=True)

# ================== SEKUENS ==================

def posisiA(device):
    pick_payload(device, get_posisi_awal())
    place_payload(device, get_predropzone_posA())
    ke_posisi_awal(device)

def posisiB(device):
    pick_payload(device, get_posisi_awal())
    place_payload(device, get_predropzone_posB())
    ke_posisi_awal(device)

def posisiC(device):
    pick_payload(device, get_posisi_awal())
    place_payload(device, get_predropzone_posC())
    ke_posisi_awal(device)

def posisiD(device):
    pick_payload(device, get_posisi_awal())
    place_payload(device, get_predropzone_posD())
    ke_posisi_awal(device)
