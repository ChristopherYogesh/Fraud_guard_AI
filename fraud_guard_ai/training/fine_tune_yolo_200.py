import os
import shutil
import sys
from pathlib import Path

# Add root fraud_guard_ai to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ultralytics import YOLO

def fine_tune_yolo_200_epochs(
    epochs=200,
    batch=16,
    imgsz=640,
    device=0,   
    patience=25,
    learning_rate=0.001
):
    """
    Fine-tunes the existing trained YOLOv8 model for 200 epochs on the RTX 4050 GPU.
    Loads models/weights/best_yolov8n.pt if present; otherwise falls back to yolov8n.pt.
    """
    print("==================================================================")
    print("  FRAUD GUARD AI — YOLOV8 200-EPOCH FINE-TUNING PIPELINE")
    print("==================================================================")

    # 1. Dataset YAML Path
    yaml_path = Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8\data_training.yaml")
    if not yaml_path.exists():
        from prepare_dataset import prepare_dataset_yaml
        yaml_path = prepare_dataset_yaml()

    print(f"[Dataset Config] -> {yaml_path}")

    # 2. Locate Existing Pretrained / Trained Weights
    weights_dir = Path(__file__).resolve().parent.parent / 'models' / 'weights'
    weights_dir.mkdir(parents=True, exist_ok=True)
    existing_best = weights_dir / 'best_yolov8n.pt'

    if existing_best.exists():
        starting_weights = str(existing_best)
        print(f"[Model Checkpoint] -> Found existing trained model: {starting_weights}")
        print("[Mode] -> Continuing Fine-Tuning from existing weights...")
    else:
        starting_weights = 'yolov8n.pt'
        print(f"[Model Checkpoint] -> Loading base YOLOv8n weights ({starting_weights})...")

    # 3. Initialize YOLO Model
    model = YOLO(starting_weights)

    # 4. Launch 200 Epochs Training on RTX 4050 (device 0)
    runs_dir = Path(__file__).resolve().parent / 'runs' / 'tune_200_epochs'
    print(f"\n[Training Parameters]")
    print(f"  - Target Epochs : {epochs}")
    print(f"  - Batch Size    : {batch}")
    print(f"  - Image Size    : {imgsz}x{imgsz}")
    print(f"  - GPU Device    : {device} (NVIDIA CUDA)")
    print(f"  - Early Stopping: {patience} epochs patience")
    print(f"  - Initial LR    : {learning_rate}")
    print(f"  - Output Runs   : {runs_dir}\n")

    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        patience=patience,
        lr0=learning_rate,
        lrf=0.01,
        optimizer='AdamW',
        cos_lr=True,
        plots=True,
        save=True,
        amp=True,  # Automatic Mixed Precision for RTX 4050
        project=str(runs_dir),
        name='yolov8_theft_200',
        exist_ok=True,
        verbose=True
    )

    # 5. Overwrite the main production weights with the new best model
    new_best = runs_dir / 'yolov8_theft_200' / 'weights' / 'best.pt'
    target_production_weights = weights_dir / 'best_yolov8n.pt'

    if new_best.exists():
        shutil.copy(str(new_best), str(target_production_weights))
        print(f"\n[SUCCESS] Fine-tuning finished successfully!")
        print(f"[Updated Weights] -> New best model saved to: {target_production_weights}")
    else:
        model.save(str(target_production_weights))
        print(f"\n[SUCCESS] Model saved directly to: {target_production_weights}")

    # 6. Run Validation on the fine-tuned model
    print("\n[Evaluating Fine-Tuned Model on Test Split]...")
    val_results = model.val(data=str(yaml_path), split='test')
    print(f"Test mAP50    : {val_results.box.map50:.4f}")
    print(f"Test mAP50-95 : {val_results.box.map:.4f}")

    return target_production_weights

if __name__ == '__main__':
    # You can change epochs here (default: 200)
    fine_tune_yolo_200_epochs(epochs=200, batch=16, imgsz=640, device=0, patience=25)
