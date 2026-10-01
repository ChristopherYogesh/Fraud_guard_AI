import os
import glob
import time
import json
from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

class ActivityCNN(nn.Module):
    """
    Compact Deep CNN for Surveillance Activity Classification (Chapter 5 Architecture)
    Input: (B, 3, 128, 128)
    Output: Logits for 3 classes: [Normal, Suspicious, Theft]
    """
    def __init__(self, num_classes=3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 64x64
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 32x32
            
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2)   # 16x16
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.classifier(self.features(x))

class SurveillanceDataset(Dataset):
    """Surveillance Activity Dataset reading from local Roboflow dataset."""
    def __init__(self, image_paths, labels, img_size=(128, 128), augment=False):
        self.image_paths = image_paths
        self.labels = labels
        self.img_size = img_size
        self.augment = augment

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        label = self.labels[idx]
        
        img = cv2.imread(path)
        if img is None:
            img = np.zeros((self.img_size[0], self.img_size[1], 3), dtype=np.uint8)
        else:
            img = cv2.resize(img, self.img_size)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
        if self.augment:
            if np.random.rand() > 0.5:
                img = cv2.flip(img, 1)  # Horizontal flip
            # Random brightness
            factor = np.random.uniform(0.85, 1.15)
            img = np.clip(img * factor, 0, 255).astype(np.uint8)

        # Min-Max Normalization to [0, 1] per Section 4.2
        norm = (img.astype(np.float32) / 255.0).transpose(2, 0, 1)
        return torch.tensor(norm, dtype=torch.float32), torch.tensor(label, dtype=torch.long)

def build_dataset_lists(dataset_base):
    """Parses local dataset and builds balanced dataset of Normal (0), Suspicious (1), Theft (2)."""
    train_paths, train_labels = [], []
    val_paths, val_labels = [], []

    for split, paths_list, labels_list in [('train', train_paths, train_labels), ('valid', val_paths, val_labels)]:
        img_dir = Path(dataset_base) / split / 'images'
        lbl_dir = Path(dataset_base) / split / 'labels'
        
        for img_file in list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.png')):
            lbl_file = lbl_dir / f"{img_file.stem}.txt"
            label = 0  # Normal default
            if lbl_file.exists():
                with open(lbl_file, 'r') as f:
                    content = f.read().strip().split('\n')
                    for line in content:
                        parts = line.strip().split()
                        if parts:
                            cls_id = parts[0]
                            if cls_id == '1':  # Shoplifting / Theft
                                label = 2
                            elif cls_id == '0' and len(parts) >= 5 and float(parts[4]) > 0.5:
                                # Deep interaction / large object manipulation tagged as suspicious
                                label = 1
            paths_list.append(str(img_file))
            labels_list.append(label)

    return (train_paths, train_labels), (val_paths, val_labels)

def train_cnn(epochs=15, batch_size=32, lr=0.001):
    print("=========================================================")
    print("  FRAUD GUARD AI — CNN ACTIVITY CLASSIFIER TRAINING")
    print("=========================================================")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[Hardware] Using Compute Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    dataset_dir = r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8"
    (train_p, train_l), (val_p, val_l) = build_dataset_lists(dataset_dir)
    print(f"[Dataset] Train samples: {len(train_p)}, Validation samples: {len(val_p)}")

    train_ds = SurveillanceDataset(train_p, train_l, augment=True)
    val_ds = SurveillanceDataset(val_p, val_l, augment=False)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = ActivityCNN(num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
    best_acc = 0.0

    output_dir = Path(__file__).resolve().parent.parent / 'models' / 'weights'
    output_dir.mkdir(parents=True, exist_ok=True)
    best_model_path = output_dir / 'activity_cnn.pth'

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

        print(f"Epoch [{epoch:02d}/{epochs:02d}] "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")

        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), str(best_model_path))

    print(f"\n[Success] Training complete! Best Validation Accuracy: {best_acc*100:.2f}%")
    print(f"[Model Saved] Weights preserved at: {best_model_path}")

    # Save metrics history JSON
    history_file = output_dir / 'cnn_training_history.json'
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"[Metrics Saved] Training history written to: {history_file}")

    return best_model_path, history

if __name__ == '__main__':
    train_cnn(epochs=12, batch_size=32)
