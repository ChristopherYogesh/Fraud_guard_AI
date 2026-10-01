import os
from pathlib import Path
import yaml

def prepare_dataset_yaml():
    """Generates absolute path data.yaml for YOLOv8 training."""
    dataset_dir = Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8")
    
    if not dataset_dir.exists():
        print(f"[Error] Dataset directory not found: {dataset_dir}")
        return None
        
    train_images = dataset_dir / "train" / "images"
    val_images = dataset_dir / "valid" / "images"
    test_images = dataset_dir / "test" / "images"
    
    config = {
        'path': str(dataset_dir.as_posix()),
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': 2,
        'names': ['normal', 'shoplifting']
    }
    
    output_yaml = dataset_dir / "data_training.yaml"
    with open(output_yaml, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
        
    print(f"[prepare_dataset] Generated resolved dataset config at: {output_yaml}")
    return output_yaml

if __name__ == '__main__':
    prepare_dataset_yaml()
