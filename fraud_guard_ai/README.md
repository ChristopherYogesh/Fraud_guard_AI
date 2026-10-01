# FRAUD GUARD AI — Intelligent Real-Time Theft & Anomaly Detection System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Framework: Flask 3](https://img.shields.io/badge/Framework-Flask%203-black.svg)](https://flask.palletsprojects.com/)
[![Vision: YOLOv8](https://img.shields.io/badge/Detection-Ultralytics%20YOLOv8-green.svg)](https://ultralytics.com/)
[![Deep Learning: PyTorch](https://img.shields.io/badge/PyTorch-2.5%2BCUDA-orange.svg)](https://pytorch.org/)
[![Design: Blueprint UI](https://img.shields.io/badge/Theme-Drafting%20Paper%20%2F%20Cyanotype-0ea5e9.svg)]()

> **Project Report Title**: FRAUD GUARD AI: AN INTELLIGENT REAL-TIME THEFT DETECTION SYSTEM USING CNN AND YOLO  
> **Institution**: Dr. M.G.R. Educational and Research Institute (B.Tech CSE DS&AI)  
> **Product Architecture**: EyeMatrix Security Engine

---

## 1. Executive Summary & Core Innovation

Traditional commercial surveillance relies heavily on human operators observing dozens of passive CCTV streams simultaneously. Research demonstrates human attentiveness degrades precipitously after 20 minutes of passive observation, leading to delayed responses and unrecovered inventory shrinkage.

**FRAUD GUARD AI** addresses this challenge through a **dual-path real-time deep learning architecture**:
1. **Object Detection & Localization (YOLOv8n)**: Real-time identification of persons, bags, backpacks, merchandise, and concealment interactions with bounding boxes.
2. **Activity Classification (Deep CNN)**: Frame and crop-level behavioral pattern classification into **Normal**, **Suspicious**, and **Theft** states.
3. **Decision Fusion Engine**: Blends spatial bounding box coordinates with temporal activity probability vectors, calculating a normalized Threat Score and Risk Classification (**LOW**, **MEDIUM**, **HIGH**, **CRITICAL**).
4. **Automated Incident Response**: Triggers instant Web Audio warning sirens, on-screen flashing banners, database logging with evidence frame preservation, and daily/weekly/monthly audit reporting.

---

## 2. System Architecture

```
                       CCTV / Camera / Video Input
                                  │
                                  ▼
                         Frame Extraction
                                  │
                                  ▼
                    Pre-processing & Normalization
                    (Resize 128x128 & 640x640, [0, 1])
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
      [ YOLOv8 Detector ]              [ CNN Activity Classifier ]
   Localizes Persons & Objects          Classifies Behavior Patterns
   (person, bag, interaction)           (Normal, Suspicious, Theft)
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                Feature / Decision Fusion Engine
                                  │
                        Threat Level Evaluated
                                  │
               ┌──────────────────┴──────────────────┐
        [ If Threat ]                         [ If Normal ]
               │                                     │
               ▼                                     ▼
      Immediate Alert Dispatch              Passive Feed Update
      - Web Audio Warning Chime             - Telemetry Stream
      - High-Contrast On-Screen Banner      - System Health Ping
      - SQLite Incident Persistence
      - Evidence JPEG Capture
                                  │
                                  ▼
                Surveillance Monitoring Console
```

---

## 3. Technology Stack

| Layer | Component | Specification |
|---|---|---|
| **Deep Learning** | PyTorch 2.5.1+cu121 | NVIDIA CUDA acceleration (RTX 4050 Laptop GPU / FP16) |
| **Object Detection** | Ultralytics YOLOv8 | YOLOv8n fine-tuned on local Roboflow retail dataset |
| **Computer Vision** | OpenCV (cv2) | Frame capture, BGR normalization, MJPEG streaming |
| **Backend Framework** | Flask 3.1+ | Application-factory pattern, 11 Modular Blueprints |
| **Authentication** | Flask-Login | Session-based authentication, RBAC (Admin, Guard) |
| **Database & ORM** | SQLite + Flask-SQLAlchemy | 6 Relational tables (Users, Incidents, Alerts, Reports, Settings, Logs) |
| **Data Visualisation** | Chart.js | Vendored locally for complete offline operability |
| **Reporting & Export** | ReportLab + openpyxl | Automated Daily/Weekly/Monthly PDF & Excel spreadsheets |
| **Hardware Telemetry** | psutil + nvidia-smi | Real-time CPU, RAM, Disk, and GPU performance stats |
| **Design Language** | Blueprint Design System | Drafting Paper (Light) and Cyanotype (Dark) themes |

---

## 4. Application Modules

The system provides 11 operational modules accessible via the persistent left-hand sidebar:

1. **Dashboard (`/dashboard`)**: At-a-glance surveillance KPIs (Today's Detections, Total Alerts, Critical Flags, Threat Posture), 7-day trend chart, risk level doughnut, recent events, and hardware health.
2. **Live Camera (`/live`)**: Low-latency Motion-JPEG stream (`/video_feed`) with an **AI Engine Telemetry Side Panel** displaying classification, confidence, latency ms, FPS, and GPU stats, with start/stop, snapshot, and fullscreen controls.
3. **Upload Video (`/upload`)**: Drag-and-drop offline video ingestion for auditing DVR backups and forensic analysis.
4. **Detection History (`/history`)**: Searchable, filterable incident log with thumbnail modal inspection, status updates, and CSV/PDF export.
5. **Alerts Feed (`/alerts`)**: Prioritised real-time notification stream with individual acknowledgment, bulk clearing, and audible warning toggle.
6. **Analytics (`/analytics`)**: Actionable charts (14-day trends, hourly breakdown 00:00-23:00, incident classifications, risk distribution).
7. **Security Reports (`/reports`)**: On-demand Daily, Weekly, and Monthly reports exported as styled PDFs (ReportLab) or Excel sheets (openpyxl).
8. **Employee Access (`/employees`)**: Administrator-only personnel directory (add staff, toggle status, change role, reset passwords).
9. **Settings (`/settings`)**: Detection sensitivity calibration (Low/Medium/High), default camera source, audio chime toggle, theme switcher, and data retention rules.
10. **Profile (`/profile`)**: Personal identification management and secure credential updates.
11. **REST API (`/api/*`)**: Endpoints for telemetry, unread alerts count, health checks, and verified model performance metrics.

---

## 5. Model Performance Metrics (Report Chapter 7)

Tested against the local Roboflow retail shoplifting surveillance dataset:

### Class-wise Performance Metrics (Table 7.1)
| Activity Class | Precision | Recall | F1-Score |
|---|---|---|---|
| **Normal** | 0.98 | 0.97 | 0.975 |
| **Suspicious** | 0.94 | 0.93 | 0.935 |
| **Theft** | 0.96 | 0.95 | 0.955 |
| **Overall (Average)** | **0.96** | **0.95** | **96.8% Accuracy** |

### Benchmark Comparison with Existing Surveillance Approaches (Table 7.2)
| Method | Approach | Accuracy | Real-Time |
|---|---|---|---|
| Background Subtraction + SVM | Handcrafted Features | 78.5% | Yes |
| 3D CNN (C3D) | Spatio-temporal CNN | 89.2% | Limited |
| Faster R-CNN + LSTM | Two-stage Detection | 92.4% | No |
| YOLOv8 + DeepSORT | Detection + Tracking | 94.0% | Yes |
| **Fraud Guard AI (Proposed)** | **CNN — YOLOv8** | **96.8%** | **Yes (15-30 FPS)** |

---

## 6. Installation & Execution Guide

### Prerequisites
- Windows 10/11 (or Linux)
- Python 3.10+ (Python 3.11 recommended)
- NVIDIA GPU with CUDA support recommended (e.g., RTX 4050)

### Setup Instructions

1. **Clone or Navigate to the Workspace**:
   ```bash
   cd "D:\college\mini project"
   ```

2. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies** (if creating a new environment):
   ```bash
   pip install -r fraud_guard_ai/requirements.txt
   ```

4. **Prepare Dataset Configuration & Train Models**:
   ```bash
   python fraud_guard_ai/training/prepare_dataset.py
   python fraud_guard_ai/training/train_cnn.py
   python fraud_guard_ai/training/evaluate.py
   ```

5. **Launch Fraud Guard AI Application**:
   ```bash
   python fraud_guard_ai/app.py
   ```

6. **Open in Browser**:
   Navigate to `http://127.0.0.1:5000`

---

## 7. Default Operator Credentials

| Role | Username | Password | Privileges |
|---|---|---|---|
| **System Administrator** | `admin` | `admin123` | Full access: All modules, employee management, system settings |
| **Security Guard** | `guard` | `guard123` | Monitoring: Dashboard, Live camera, History, Alerts, Analytics |

---

## 8. Automated Testing Suite

To run the complete automated test suite:
```bash
python -m unittest discover -s fraud_guard_ai/tests -p "test_*.py"
```

---

## 9. License & Academic Attribution
Developed for the **Department of Data Science and Artificial Intelligence**, Dr. M.G.R. Educational and Research Institute. Licensed under the MIT License.
