import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import time
import hand_tracker

print("Testing camera and hand tracker performance...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 60)

tracker = hand_tracker.HandTracker(max_hands=1)

t_read_list = []
t_proc_list = []

for i in range(30):
    t0 = time.time()
    ret, frame = cap.read()
    t1 = time.time()
    if not ret:
        print("Failed to read frame")
        break
    t_read_list.append((t1 - t0) * 1000)

    t2 = time.time()
    _, landmarks, _ = tracker.process_frame(frame)
    t3 = time.time()
    t_proc_list.append((t3 - t2) * 1000)

cap.release()

if t_read_list and t_proc_list:
    avg_read = sum(t_read_list) / len(t_read_list)
    avg_proc = sum(t_proc_list) / len(t_proc_list)

    print(f"Avg Camera Read Time: {avg_read:.2f} ms (Camera FPS cap: {1000/avg_read if avg_read>0 else 0:.1f} FPS)")
    print(f"Avg Hand Tracker Process Time: {avg_proc:.2f} ms (Tracker max FPS: {1000/avg_proc if avg_proc>0 else 0:.1f} FPS)")
    print(f"Combined Frame Time: {avg_read + avg_proc:.2f} ms (Real Total FPS: {1000/(avg_read + avg_proc):.1f} FPS)")
