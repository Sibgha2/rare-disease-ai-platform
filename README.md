# RareDiseaseAI — Multimodal Rare Disease Diagnosis Platform

An advanced, clinical-grade decision support platform designed to analyze multimodal patient data (MRI/CT scans, genomic sequences, clinical symptoms, and lab panels) using AI ensemble logic to identify rare genetic conditions.

---

## 🌟 Key Features

### 1. Unified Multimodal Diagnostic Intake
* Supports multi-format diagnostic file uploads:
  * **Imaging Scans**: DICOM (`.dcm`), NIfTI (`.nii`, `.nii.gz`) — *Mandatory*
  * **Genetics**: CSV, JSON variants — *Required 2 of 3 optional modalities*
  * **Clinical Notes**: TXT, PDF symptoms
  * **Lab Panels**: CSV, XLSX biomarker reports

### 2. Live Diagnostics Pipeline Status Tracker
* Monitors progress in real-time through **9 stages**:
  1. Intake Form Submission
  2. Data Quality & Dependency Validation
  3. Parallel Modality Feature Extraction (Concurrent Workers)
  4. Ensemble ML Model Inference (Local/API)
  5. Scan Annotation & Explanation Chart Generation
  6. PDF Diagnostic Report Compilation
  7. PostgreSQL Database Record Entry
  8. Doctor Email Notification (Local `.eml` save)
  9. Remote Hospital Dashboard Sync API Callback

### 3. Explainable AI (XAI) & Scan Annotation
* **Interactive Scan Inspector**: Visualizes dynamic, disease-specific region-of-interest (ROI) overlays (such as *Caudate Nucleus Atrophy* for Huntington's or *Lung Infiltrates* for Cystic Fibrosis) with brightness and contrast sliders.
* **XAI Graph Network**: Interactive nodes model depicting structural weight contributions per input modality using Vis.js.
* **Global Registry Hotspots**: Visualizes disease registry prevalence globally.
* **Collaboration Hub**: Simulates telehealth review sessions from international specialists.

### 4. Professional SuperAdmin Portal
* Sidebar interface at `/admin.html` tracking stats, listing active sessions, and allowing administrators to register or delete doctor credentials with a live system activity feed.

---

## 🛠️ Technology Stack

* **Backend**: Flask (Python 3)
* **Frontend**: Vanilla HTML5, CSS3 (Custom Glassmorphic Design), Vanilla JavaScript (SPA Model)
* **Database**: PostgreSQL (via `psycopg2`)
* **Libraries**: Matplotlib, ReportLab (PDF generator), Vis.js (Graph networks), NetworkX, Pandas, NumPy, Pydicom, Nibabel

---

## 📂 Project Directory Structure

```text
├── app.py                      # Flask Server Core & API Routes
├── pipeline.py                 # Original 9-Stage Background Pipeline Workflow
├── pipeline_annotated.py       # Hook overrides for Scan Annotation & PDF overlays
├── pdf_report.py               # Custom ReportLab PDF generator stylesheet
├── db_setup.py                 # PostgreSQL Database initializer & Tables creator
├── create_samples.py           # Generates initial mock upload datasets
├── create_extra_samples.py     # Generates extra mock datasets
├── create_system_overview_pdf.py# Generates System Architecture Overview PDF
├── test_pipeline.py            # Integration test suite for backend pipeline
├── static/
│   ├── index.html              # Main App UI (Diagnostics Workspace)
│   ├── login.html              # Doctor/Admin Login Workspace
│   ├── admin.html              # SuperAdmin Management Portal
│   ├── app.js                  # Frontend Controller script (Vis.js, Tabs, Polling)
│   ├── styles.css              # Custom responsive stylesheet system
│   └── doctors.json            # Clinician database registry storage
├── annotations/                # Stored annotated scans
├── explanations/               # Stored modality attention charts
├── reports/                    # Generated PDF reports
└── sent_emails/                # Sent clinician report backups (.eml)
```

---

## 🚀 Getting Started

### 1. Database Setup
Ensure PostgreSQL is running locally on port `5432` with a `postgres` database. The server automatically attempts to initialize tables upon startup, but you can force setup by running:
```bash
python db_setup.py
```

### 2. Generate Sample Files
To seed the `sample_data/` directory with mock patient uploads (MRI scans, genetic variants, clinical text, and labs), run:
```bash
python create_samples.py
python create_extra_samples.py
```

### 3. Launch Flask Server
Start the development server:
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your web browser.

### 4. Running Integration Tests
To test the entire 9-stage workflow synchronously (asserting database inserts, PDF reports, chart generations, and annotation outputs), run:
```bash
python test_pipeline.py
```

---

## 🔑 Demo Access Credentials

| Portal / Role | URL | Email | Password |
|---|---|---|---|
| **SuperAdmin** | `/admin.html` | `admin@raredisease.ai` | `Admin@123` |
| **Doctor / Clinician** | `/login.html` | `sarah.chen@hospital.com` | `Doctor@123` |
| **Doctor / Clinician** | `/login.html` | `m.adeyemi@medcenter.org` | `Doctor@123` |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///c:/Users/sibgh/Downloads/Multimodal%20Rare%20Disease%20Diagnosis%20System/LICENSE) file for details.

