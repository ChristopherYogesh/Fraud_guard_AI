import os
import sys
import glob
from pathlib import Path

# Add root fraud_guard_ai to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import cv2
import torch
from services.detector_engine import FraudDetectorEngine

def test_inference():
    print("=========================================================")
    print("  FRAUD GUARD AI — STANDALONE INFERENCE VERIFICATION")
    print("=========================================================")

    engine = FraudDetectorEngine()
    test_dir = Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8\test\images")
    output_dir = Path(__file__).resolve().parent.parent / 'data' / 'evidence'
    output_dir.mkdir(parents=True, exist_ok=True)

    test_images = list(test_dir.glob('*.jpg'))[:5]
    if not test_images:
        print(f"[Warning] No test images found in {test_dir}")
        return

    print(f"[Testing] Running inference on {len(test_images)} test samples...")
    for idx, img_path in enumerate(test_images, 1):
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        annotated, telemetry = engine.analyze_frame(frame)
        out_file = output_dir / f"test_out_{idx}.jpg"
        cv2.imwrite(str(out_file), annotated)

        print(f"Sample #{idx}: {img_path.name}")
        print(f"  -> Activity: {telemetry['activity']}")
        print(f"  -> Threat Level: {telemetry['risk_level']}")
        print(f"  -> Confidence: {telemetry['confidence_pct']}")
        print(f"  -> Objects: {telemetry['objects_detected']}")
        print(f"  -> Latency: {telemetry['inference_time_ms']} ms")
        print(f"  -> Output Saved: {out_file}\n")

if __name__ == '__main__':
    test_inference()
