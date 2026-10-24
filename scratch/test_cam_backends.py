import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import time

def test_cam(name, backend, fourcc, width, height, fps_target):
    print(f"\n--- Testing {name} ---")
    if backend is not None:
        cap = cv2.VideoCapture(0, backend)
    else:
        cap = cv2.VideoCapture(0)
        
    if not cap.isOpened():
        print("Failed to open camera.")
        return

    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    if width and height:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps_target:
        cap.set(cv2.CAP_PROP_FPS, fps_target)

    # Read a few warm-up frames
    for _ in range(5):
        cap.read()

    times = []
    for _ in range(30):
        t0 = time.time()
        ret, frame = cap.read()
        t1 = time.time()
        if ret:
            times.append((t1 - t0) * 1000)
    cap.release()

    if times:
        avg_ms = sum(times) / len(times)
        actual_fps = 1000 / avg_ms if avg_ms > 0 else 0
        w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps_prop = cap.get(cv2.CAP_PROP_FPS)
        print(f"Result: Avg Read = {avg_ms:.2f} ms | FPS = {actual_fps:.1f} | Res = {int(w)}x{int(h)} | Prop FPS = {fps_prop}")

test_cam("CAP_DSHOW (Default)", cv2.CAP_DSHOW, None, 640, 480, 60)
test_cam("CAP_DSHOW + MJPG", cv2.CAP_DSHOW, 'MJPG', 640, 480, 60)
test_cam("CAP_DSHOW + MJPG (320x240)", cv2.CAP_DSHOW, 'MJPG', 320, 240, 60)
test_cam("CAP_MSMF (Media Foundation)", cv2.CAP_MSMF, None, 640, 480, 60)
test_cam("CAP_MSMF + MJPG", cv2.CAP_MSMF, 'MJPG', 640, 480, 60)
test_cam("CAP_ANY (Default OpenCV)", None, None, 640, 480, 60)
test_cam("CAP_ANY + MJPG (320x240)", None, 'MJPG', 320, 240, 60)
