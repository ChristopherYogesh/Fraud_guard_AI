import os
import sys
import json
import time
from pathlib import Path

# Add root fraud_guard_ai to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from training.train_cnn import ActivityCNN, SurveillanceDataset, build_dataset_lists

def fine_tune_cnn_200_epochs(
    epochs=200,
    batch_size=32,
    lr=0.0003,
    patience=25
):
    """
    Fine-tunes the CNN Behavioral Classifier for 200 epochs on the RTX 4050 GPU.
    Loads existing models/weights/activity_cnn.pth checkpoint if available.
    """
    print("==================================================================")
    print("  FRAUD GUARD AI — CNN CLASSIFIER 200-EPOCH FINE-TUNING PIPELINE")
    print("==================================================================")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[Hardware] Compute Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 1. Dataset Preparation
    dataset_dir = r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8"
    (train_p, train_l), (val_p, val_l) = build_dataset_lists(dataset_dir)
    print(f"[Dataset] Train samples: {len(train_p)}, Validation samples: {len(val_p)}")

    train_ds = SurveillanceDataset(train_p, train_l, augment=True)
    val_ds = SurveillanceDataset(val_p, val_l, augment=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # 2. Model Initialization & Pretrained Weights Loading
    model = ActivityCNN(num_classes=3).to(device)
    weights_dir = Path(__file__).resolve().parent.parent / 'models' / 'weights'
    weights_dir.mkdir(parents=True, exist_ok=True)
    existing_cnn = weights_dir / 'activity_cnn.pth'

    if existing_cnn.exists():
        print(f"[Model Checkpoint] Loading existing trained weights: {existing_cnn}")
        try:
            model.load_state_dict(torch.load(str(existing_cnn), map_location=device, weights_only=True))
            print("[Mode] Successfully loaded existing weights. Commencing fine-tuning...")
        except Exception as e:
            print(f"[Warning] Could not load checkpoint ({e}). Training from baseline initialization.")
    else:
        print("[Mode] No prior weights found. Training from baseline initialization...")

    criterion = nn.CrossEntropyLoss()
    # Use slightly lower learning rate (0.0003) for fine-tuning to preserve learned representations
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=20, T_mult=2)

    history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
    best_val_acc = 0.0
    epochs_no_improve = 0

    print(f"\n[Fine-Tuning Configuration]")
    print(f"  - Target Epochs : {epochs}")
    print(f"  - Batch Size    : {batch_size}")
    print(f"  - Initial LR    : {lr}")
    print(f"  - Early Stop    : {patience} epochs patience\n")

    for epoch in range(1, epochs + 1):
        # Training Phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

        scheduler.step()
        train_loss = running_loss / total
        train_acc = correct / total

        # Validation Phase
        model.eval()
        v_running_loss = 0.0
        v_correct = 0
        v_total = 0

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)

                v_running_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                v_correct += (preds == targets).sum().item()
                v_total += targets.size(0)

        val_loss = v_running_loss / v_total
        val_acc = v_correct / v_total

        history['train_loss'].append(round(train_loss, 4))
        history['val_loss'].append(round(val_loss, 4))
        history['train_acc'].append(round(train_acc, 4))
        history['val_acc'].append(round(val_acc, 4))

        improved = "*" if val_acc > best_val_acc else " "
        print(f"Epoch [{epoch:03d}/{epochs:03d}] "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}% {improved}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            torch.save(model.state_dict(), str(existing_cnn))
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"\n[Early Stopping] No improvement in validation accuracy for {patience} epochs. Stopping early at epoch {epoch}.")
                break

    print(f"\n[SUCCESS] Fine-tuning concluded!")
    print(f"[Best Validation Accuracy] -> {best_val_acc*100:.2f}%")
    print(f"[Model Checkpoint Updated] -> {existing_cnn}")

    # Update training history
    history_file = weights_dir / 'cnn_training_history.json'
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

    return existing_cnn

if __name__ == '__main__':
    fine_tune_cnn_200_epochs(epochs=200, batch_size=32, lr=0.0003, patience=25)
