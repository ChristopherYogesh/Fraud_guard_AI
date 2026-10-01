import os
import shutil
from pathlib import Path
from ultralytics import YOLO

def train_yolo(epochs=100, imgsz=640, batch=16, device=0):
    print("=========================================================")
    print("  FRAUD GUARD AI — YOLOV8 THEFT DETECTOR TRAINING")
    print("=========================================================")
    
    yaml_path = Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8\data_training.yaml")
    if not yaml_path.exists():
        from prepare_dataset import prepare_dataset_yaml
        yaml_path = prepare_dataset_yaml()

    weights_dir = Path(__file__).resolve().parent.parent / 'models' / 'weights'
    weights_dir.mkdir(parents=True, exist_ok=True)
    target_best_pt = weights_dir / 'best_yolov8n.pt'

    print(f"[Dataset Config] {yaml_path}")
    print(f"[Device] Using GPU device {device} (RTX 4050 Laptop GPU)")

    # Load base YOLOv8n model
    model = YOLO('yolov8n.pt')
    
    # Train model
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(Path(__file__).resolve().parent / 'runs'),
        name='fraudguard_yolov8',
        exist_ok=True,
        verbose=True
    )

    # Locate and copy best.pt
    run_best = Path(__file__).resolve().parent / 'runs' / 'fraudguard_yolov8' / 'weights' / 'best.pt'
    if run_best.exists():
        shutil.copy(str(run_best), str(target_best_pt))
        print(f"\n[Success] Best YOLOv8 model copied to: {target_best_pt}")
    else:
        # Fallback to model export
        model.save(str(target_best_pt))
        print(f"\n[Saved] YOLOv8 model saved to: {target_best_pt}")

    return target_best_pt

if __name__ == '__main__':
    train_yolo(epochs=5, imgsz=640, batch=16)
