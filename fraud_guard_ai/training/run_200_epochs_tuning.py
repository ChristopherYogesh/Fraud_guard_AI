import argparse
import sys
from pathlib import Path

# Add root fraud_guard_ai to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from training.fine_tune_yolo_200 import fine_tune_yolo_200_epochs
from training.fine_tune_cnn_200 import fine_tune_cnn_200_epochs
from training.evaluate import generate_evaluation_artifacts

def main():
    parser = argparse.ArgumentParser(description="FRAUD GUARD AI — 200 Epochs Fine-Tuning Pipeline")
    parser.add_argument('--model', type=str, choices=['yolo', 'cnn', 'all'], default='yolo',
                        help="Which model to fine-tune ('yolo', 'cnn', or 'all'). Default: yolo")
    parser.add_argument('--epochs', type=int, default=200,
                        help="Number of epochs to train (Default: 200)")
    parser.add_argument('--batch', type=int, default=16,
                        help="Batch size (Default: 16)")
    parser.add_argument('--patience', type=int, default=25,
                        help="Early stopping patience epochs (Default: 25)")
    parser.add_argument('--device', type=str, default='0',
                        help="GPU device id ('0' for RTX 4050 or 'cpu'). Default: 0")

    args = parser.parse_args()

    print("==================================================================")
    print("      FRAUD GUARD AI — DEEP LEARNING MODEL TUNING CONSOLE")
    print("==================================================================")
    print(f"Target Selection : {args.model.upper()}")
    print(f"Epochs Target    : {args.epochs}")
    print(f"Batch Size       : {args.batch}")
    print(f"Device           : GPU {args.device}")
    print("==================================================================\n")

    if args.model in ['yolo', 'all']:
        print("\n>>> STARTING YOLOV8 THEFT DETECTOR 200-EPOCH FINE-TUNING...\n")
        dev = int(args.device) if args.device.isdigit() else args.device
        fine_tune_yolo_200_epochs(
            epochs=args.epochs,
            batch=args.batch,
            device=dev,
            patience=args.patience
        )

    if args.model in ['cnn', 'all']:
        print("\n>>> STARTING PYTORCH CNN ACTIVITY CLASSIFIER 200-EPOCH FINE-TUNING...\n")
        fine_tune_cnn_200_epochs(
            epochs=args.epochs,
            batch_size=args.batch * 2,
            patience=args.patience
        )

    # Re-generate performance curves and evaluation metrics
    print("\n>>> RE-EVALUATING AND UPDATING METRICS CHARTS (FIG 7.1 & FIG 7.2)...")
    generate_evaluation_artifacts()
    print("\n[COMPLETE] All fine-tuning and evaluation routines concluded successfully!")

if __name__ == '__main__':
    main()
