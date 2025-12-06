#!/usr/bin/env python3
"""Quick test to verify camera works with OpenCV (used by Project Leroy)"""
import cv2
import sys

print("Testing camera with OpenCV...")
print("(This is what Project Leroy uses)")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ FAILED: Could not open camera")
    print("\nTroubleshooting:")
    print("  1. Check camera is connected")
    print("  2. Check user is in video group: groups")
    print("  3. Try: sudo usermod -aG video $USER")
    sys.exit(1)

print("✓ Camera opened successfully")

# Try to read a frame
ret, frame = cap.read()
if not ret or frame is None:
    print("❌ FAILED: Could not read frame")
    cap.release()
    sys.exit(1)

height, width = frame.shape[:2]
print(f"✓ Frame captured: {width}x{height}")

# Get camera properties
actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"✓ Camera properties:")
print(f"    Resolution: {actual_width}x{actual_height}")
print(f"    FPS: {fps}")
print(f"    Format: {frame.shape}")

# Test setting resolution (like Project Leroy does)
print("\nTesting resolution changes...")
test_resolutions = [
    (1280, 960),   # Common detection resolution
    (4056, 3040),  # Full 12MP
]

for w, h in test_resolutions:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Requested: {w}x{h} → Actual: {actual_w}x{actual_h}")

cap.release()
print("\n✅ Camera test PASSED - Ready for Project Leroy!")
