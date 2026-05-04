import cv2
import numpy as np

def preprocess(frame):
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    return hsv

COLOR_RANGES = {
    "red1": ([0,120,70], [10,255,255]),
    "red2": ([170,120,70], [180,255,255]),
    "green": ([36,50,50], [86,255,255]),
    "blue": ([100,50,50], [130,255,255]),
    "yellow": ([20,100,100], [35,255,255]),
}

def get_mask(hsv, color):
    if color == "red":
        mask1 = cv2.inRange(hsv, np.array(COLOR_RANGES["red1"][0]), np.array(COLOR_RANGES["red1"][1]))
        mask2 = cv2.inRange(hsv, np.array(COLOR_RANGES["red2"][0]), np.array(COLOR_RANGES["red2"][1]))
        return mask1 | mask2
    else:
        lower, upper = COLOR_RANGES[color]
        return cv2.inRange(hsv, np.array(lower), np.array(upper))

COLORS = ["red", "green", "blue", "yellow"]

def detect_object(mask):
    # bersihkan noise
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # ambil objek terbesar
    c = max(contours, key=cv2.contourArea)

    if cv2.contourArea(c) < 100:
        return None

    # centroid pakai moments (lebih stabil)
    M = cv2.moments(c)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return (cx, cy), c

cap = cv2.VideoCapture(2, cv2.CAP_DSHOW) # ganti argumen dengan indeks kamera yang sesuai

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FPS, 30)

while not cap.isOpened():
    print("Kamera tidak bisa dibuka")
    if(cap.isOpened()):
        break

ROI_X1, ROI_Y1 = 230, 150 # dimensi bounding box
ROI_X2, ROI_Y2 = 360, 350

inside_state = {color: False for color in COLORS}

def is_inside(cx, cy):
    return ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2
    
while True:
    ret, frame = cap.read()
    if not ret:
        break

    hsv = preprocess(frame)

    for color in COLORS:
        mask = get_mask(hsv, color)
        result = detect_object(mask)

        if result:
            (cx, cy), contour = result

            # hitung orientasi
            rect = cv2.minAreaRect(contour)
            (x_rect, y_rect), (w, h), angle = rect

            # normalisasi sudut
            if w < h:
                angle = angle + 90

            angle = angle % 46

            in_box = is_inside(cx, cy)

            box = cv2.boxPoints(rect)
            box = box.astype(int)
            cv2.drawContours(frame, [box], 0, (0,255,255), 2)
            
            # state logic
            if in_box and not inside_state[color]:
                print(f"{color} MASUK ROI di ({cx},{cy}) dengan sudut {angle:.1f} deg")
                inside_state[color] = True

            elif not in_box and inside_state[color]:
                print(f"{color} KELUAR ROI")
                inside_state[color] = False

            # ===== VISUAL =====
            draw_color = (0,255,0) if in_box else (0,0,255)

            cv2.drawContours(frame, [contour], -1, draw_color, 2)
            cv2.circle(frame, (cx, cy), 5, draw_color, -1)

            cv2.putText(frame, f"{color} ({cx},{cy}) {angle:.1f} deg",
                        (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        draw_color, 1)
        else:
            if inside_state[color]:
                print(f"{color} HILANG → reset")
                inside_state[color] = False

    cv2.rectangle(frame,
              (ROI_X1, ROI_Y1),
              (ROI_X2, ROI_Y2),
              (0,255,255), 2)
    
    cv2.imshow("Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

