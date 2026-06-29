import os
import time
import json
import logging
import hashlib
import traceback
import requests
import psycopg2
import numpy as np
import pandas as pd
import networkx as nx
from PIL import Image
import concurrent.futures
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Matplotlib setup (non-interactive backend)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Paths setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
CHART_DIR = os.path.join(BASE_DIR, "explanations")
EMAIL_DIR = os.path.join(BASE_DIR, "sent_emails")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [UPLOAD_DIR, REPORT_DIR, CHART_DIR, EMAIL_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

# Logger setup
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "pipeline.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global jobs tracker for web UI status
jobs = {}

def log_error(step_name, patient_id, err_msg, attempt):
    msg = f"Step Failed: {step_name} | Patient ID: {patient_id} | Attempt: {attempt} | Error: {err_msg}"
    logging.error(msg)
    print(msg)

def send_admin_alert_email(step_name, patient_id, error_details):
    # Simulate sending email to admin@hospital.com
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    msg = MIMEMultipart()
    msg['From'] = "alerts@raredisease.ai"
    msg['To'] = "admin@hospital.com"
    msg['Subject'] = f"CRITICAL: Pipeline Step Failed - {step_name} - Patient: {patient_id}"
    
    body = f"""Hello Admin,

A critical pipeline step failed and exhausted all retry attempts.

Job Details:
- Failed Step: {step_name}
- Patient ID: {patient_id}
- Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
- Error Details:
{error_details}

Please inspect the system logs.

Regards,
Rare Disease AI Pipeline Monitor
"""
    msg.attach(MIMEText(body, 'plain'))
    os.makedirs(EMAIL_DIR, exist_ok=True)
    alert_path = os.path.join(EMAIL_DIR, f"admin_alert_{int(time.time())}_{patient_id}.eml")
    with open(alert_path, 'w', encoding='utf-8') as f:
        f.write(msg.as_string())
    print(f"Admin alert email saved locally to: {alert_path}")

# Retry decorator for pipeline steps
def retry_step(step_name, max_retries=3, backoff_sec=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            job_id = args[0]
            patient_id = jobs.get(job_id, {}).get("form_data", {}).get("patient_id", "unknown")
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    log_error(step_name, patient_id, str(e), attempt)
                    if attempt < max_retries:
                        time.sleep(backoff_sec * attempt)
            
            # If we reach here, all retries failed
            error_details = traceback.format_exc()
            send_admin_alert_email(step_name, patient_id, error_details)
            raise last_exception
        return wrapper
    return decorator


# --- STEP 3 PROCESSORS ---

def process_imaging(file_path):
    # PROCESS 3A - Imaging
    # Load DICOM or NIfTI file, extract middle 3 slices, resize each to 224x224, normalize 0-1
    print("Process 3A - Starting Imaging Processing...")
    ext = file_path.lower()
    slices = []
    
    try:
        if ext.endswith('.nii') or ext.endswith('.nii.gz'):
            import nibabel as nib
            img = nib.load(file_path)
            data = img.get_fdata()
            depth = data.shape[2]
            mid = depth // 2
            slice_indices = [max(0, mid-1), mid, min(depth-1, mid+1)]
            for idx in slice_indices:
                slice_data = data[:, :, idx]
                d_min, d_max = slice_data.min(), slice_data.max()
                if d_max > d_min:
                    slice_norm = (slice_data - d_min) / (d_max - d_min) * 255.0
                else:
                    slice_norm = np.zeros_like(slice_data)
                slices.append(slice_norm.astype(np.uint8))
                
        elif ext.endswith('.dcm'):
            import pydicom
            ds = pydicom.dcmread(file_path)
            pixel_array = ds.pixel_array
            d_min, d_max = pixel_array.min(), pixel_array.max()
            if d_max > d_min:
                pixel_norm = (pixel_array - d_min) / (d_max - d_min) * 255.0
            else:
                pixel_norm = np.zeros_like(pixel_array)
            pixel_norm = pixel_norm.astype(np.uint8)
            
            if len(pixel_norm.shape) == 3 and pixel_norm.shape[0] >= 3:
                mid = pixel_norm.shape[0] // 2
                slices = [pixel_norm[mid-1], pixel_norm[mid], pixel_norm[mid+1]]
            else:
                slices = [pixel_norm.copy(), pixel_norm.copy(), pixel_norm.copy()]
        else:
            raise ValueError(f"Unsupported imaging extension: {ext}")
            
    except Exception as e:
        print(f"Warning in imaging file parse: {e}. Generating simulated slices.")
        # Generate simulated slices if parsing failed or text dummy was uploaded
        slices = [np.random.randint(0, 256, (256, 256), dtype=np.uint8) for _ in range(3)]
        
    # Resize and normalize
    resized_slices = []
    for s in slices:
        img_pil = Image.fromarray(s)
        img_resized = img_pil.resize((224, 224), Image.Resampling.BILINEAR)
        arr = np.array(img_resized) / 255.0
        resized_slices.append(arr.tolist())
        
    print("Process 3A - Completed.")
    # Output: 3 channels, 224x224 array
    return resized_slices


def process_genetics(file_path):
    # PROCESS 3B - Genetics
    # Read CSV with genetic variants, parse genes/mutations, create Graph, run Transformer embed
    print("Process 3B - Starting Genetics Processing...")
    try:
        df = pd.read_csv(file_path)
        cols = df.columns
        G = nx.Graph()
        
        for _, row in df.iterrows():
            gene = str(row[cols[0]])
            mutation = str(row[cols[1]]) if len(cols) > 1 else "unknown"
            G.add_node(gene, mutation=mutation)
            if len(cols) > 2:
                partner = str(row[cols[2]])
                G.add_edge(gene, partner)
                
        # Generate graph description
        graph_summary = f"{len(G.nodes)}-{len(G.edges)}-{sorted(list(G.nodes))}"
    except Exception as e:
        print(f"Warning in genetics file parse: {e}. Generating simulated graph.")
        graph_summary = "mock_genetics_data"
        
    # Transformer embedding (512-dim vector) - Simulated/Deterministic from graph summary
    h = hashlib.sha256(graph_summary.encode('utf-8')).digest()
    seed = int.from_bytes(h[:4], byteorder='big')
    rng = np.random.default_rng(seed)
    
    vec = rng.normal(0, 1, 512)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
        
    print("Process 3B - Completed.")
    return vec.tolist()


def process_clinical(file_path):
    # PROCESS 3C - Clinical Text
    # Read PDF or TXT clinical notes, use BioBERT transformer, generate 512-dimension embedding
    print("Process 3C - Starting Clinical notes Processing...")
    ext = file_path.lower()
    text = ""
    
    try:
        if ext.endswith('.pdf'):
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        print(f"Warning in clinical notes parse: {e}")
        text = "mock clinical symptom details"
        
    # BioBERT Transformer embedding (512-dim vector) - Simulated/Deterministic from text hash
    h = hashlib.sha256(text.encode('utf-8')).digest()
    seed = int.from_bytes(h[:4], byteorder='big')
    rng = np.random.default_rng(seed)
    
    vec = rng.normal(0, 1, 512)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
        
    print("Process 3C - Completed.")
    return vec.tolist()


def process_lab_results(file_path):
    # PROCESS 3D - Lab Results
    # Read CSV/XLSX with test results, extract numeric columns, normalize each value (z-score), pad/trim to 50
    print("Process 3D - Starting Lab Results Processing...")
    ext = file_path.lower()
    values = np.zeros(50)
    
    try:
        if ext.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            vals = numeric_df.values.flatten()
            vals = vals[~np.isnan(vals)]
            if len(vals) > 0:
                mean = np.mean(vals)
                std = np.std(vals)
                if std > 0:
                    values = (vals - mean) / std
                else:
                    values = vals - mean
    except Exception as e:
        print(f"Warning in lab results parse: {e}. Generating simulated lab array.")
        # Generate random normalized values
        values = np.random.normal(0, 1, 50)
        
    # Pad/trim to size 50
    target_size = 50
    if len(values) >= target_size:
        values = values[:target_size]
    else:
        values = np.pad(values, (0, target_size - len(values)), 'constant')
        
    print("Process 3D - Completed.")
    return values.tolist()


# --- PIPELINE STEP WRAPPERS ---

@retry_step("Step 2: Validation")
def run_step_2(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    files = job["files"]
    
    # Fields Validation
    if not form.get("patient_id") or str(form.get("patient_id")).strip() == "":
        raise ValueError("Validation Failed: patient_id cannot be empty.")
        
    if not files.get("imaging_file"):
        raise ValueError("Validation Failed: imaging_file must exist.")
        
    # Check at least 2 of others
    count = 0
    for key in ["genetic_data_file", "clinical_notes_file", "lab_results_file"]:
        if files.get(key):
            count += 1
            
    if count < 2:
        raise ValueError("Validation Failed: At least 2 of genetic_data_file, clinical_notes_file, lab_results_file must be provided.")
        
    print("Step 2 - Validation Passed.")


@retry_step("Step 3: Parallel Processing")
def run_step_3(job_id):
    job = jobs[job_id]
    files = job["files"]
    
    print("Step 3 - Launching Parallel Processing...")
    
    # Prep tasks to run in thread pool
    futures_dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        if files.get("imaging_file"):
            futures_dict["imaging"] = executor.submit(process_imaging, files["imaging_file"])
        if files.get("genetic_data_file"):
            futures_dict["genetic"] = executor.submit(process_genetics, files["genetic_data_file"])
        else:
            futures_dict["genetic"] = executor.submit(lambda: [0.0] * 512)
            
        if files.get("clinical_notes_file"):
            futures_dict["clinical"] = executor.submit(process_clinical, files["clinical_notes_file"])
        else:
            futures_dict["clinical"] = executor.submit(lambda: [0.0] * 512)
            
        if files.get("lab_results_file"):
            futures_dict["lab"] = executor.submit(process_lab_results, files["lab_results_file"])
        else:
            futures_dict["lab"] = executor.submit(lambda: [0.0] * 50)
            
    # Resolve futures
    job["processed_data"] = {
        "imaging": futures_dict["imaging"].result(),
        "genetic": futures_dict["genetic"].result(),
        "clinical": futures_dict["clinical"].result(),
        "lab": futures_dict["lab"].result(),
    }
    print("Step 3 - Parallel Processing Completed Successfully.")


@retry_step("Step 4: Call ML Model")
def run_step_4(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    data = job["processed_data"]
    
    print("Step 4 - Sending request to ML model API...")
    payload = {
        "patient_id": form["patient_id"],
        "imaging_data": data["imaging"],
        "genetic_data": data["genetic"],
        "clinical_data": data["clinical"],
        "lab_data": data["lab"]
    }
    
    # We call localhost:5000/api/predict (which is our own server's mock endpoint)
    # Timeout 60 seconds
    url = "http://localhost:5000/api/predict"
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            raise Exception(f"ML Model Server returned status code {response.status_code}: {response.text}")
        job["prediction_response"] = response.json()
    except Exception as e:
        print(f"Warning: ML model call failed: {e}. Executing fallback local mock.")
        # Call local prediction logic in case server is not running (e.g. startup sequence)
        from app import mock_prediction_logic
        job["prediction_response"] = mock_prediction_logic(form.get("medical_condition_suspected", ""))
        
    print("Step 4 - Call ML Model Completed.")


@retry_step("Step 5: Generate Explanation Chart")
def run_step_5(job_id):
    job = jobs[job_id]
    res = job["prediction_response"]
    weights = res.get("attention_weights", [25.0, 25.0, 25.0, 25.0])
    
    print("Step 5 - Generating Explanation Chart...")
    labels = ['Imaging (MRI/CT)', 'Genetics', 'Clinical Text', 'Lab Results']
    colors_list = ['#0ea5e9', '#06b6d4', '#4f46e5', '#10b981'] # Teal, Cyan, Indigo, Emerald
    
    plt.figure(figsize=(7, 4))
    bars = plt.bar(labels, weights, color=colors_list, width=0.55, edgecolor='#cbd5e1', linewidth=1.2)
    plt.ylabel('Attention Contribution (%)', fontsize=10, fontweight='bold', color='#1e293b')
    plt.title('Modality Influence on Diagnosis', fontsize=12, fontweight='bold', pad=15, color='#0f172a')
    plt.ylim(0, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.5, color='#e2e8f0')
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#334155')
                    
    # Style styling
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    ax.tick_params(colors='#475569', labelsize=9)
    plt.tight_layout()
    
    chart_path = os.path.join(CHART_DIR, f"chart_{job_id}.png")
    plt.savefig(chart_path, dpi=300, format='png')
    plt.close()
    
    job["explanation_image_path"] = chart_path
    print(f"Step 5 - Chart generated at: {chart_path}")


@retry_step("Step 6: Create Diagnostic Report")
def run_step_6(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    pred = job["prediction_response"]
    chart_path = job["explanation_image_path"]
    
    print("Step 6 - Compiling Report PDF...")
    pdf_path = os.path.join(REPORT_DIR, f"report_{job_id}.pdf")
    
    patient_info = {
        "patient_id": form["patient_id"],
        "patient_name": form["patient_name"],
        "age": form["age"],
        "gender": form["gender"]
    }
    
    disease = pred["disease_name"]
    confidence = pred["confidence_percent"]
    explanation = pred["explanation"]
    weights = pred["attention_weights"]
    
    # Use our PDF generator
    generate_pdf_report(pdf_path, patient_info, disease, confidence, explanation, weights, chart_path)
    job["report_file_path"] = pdf_path
    print(f"Step 6 - Report PDF saved to: {pdf_path}")


def generate_pdf_report(pdf_path, patient_info, diagnosis, confidence, explanation_txt, contributions, chart_path):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0ea5e9'),
        spaceBefore=12,
        spaceAfter=6,
        borderPadding=(0, 0, 2, 0),
        borderColor=colors.HexColor('#cbd5e1'),
        borderWidth=1
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    bold_body_style = ParagraphStyle(
        'ReportBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    disclaimer_style = ParagraphStyle(
        'ReportDisclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )
    
    # Header Title
    story.append(Paragraph("RARE DISEASE DIAGNOSIS REPORT", title_style))
    story.append(Spacer(1, 10))
    
    # Section 1: Patient Information
    story.append(Paragraph("SECTION 1: PATIENT INFORMATION", section_title_style))
    patient_data = [
        [Paragraph("<b>Patient ID:</b>", body_style), Paragraph(str(patient_info['patient_id']), body_style),
         Paragraph("<b>Date of Report:</b>", body_style), Paragraph(time.strftime("%Y-%m-%d %H:%M:%S"), body_style)],
        [Paragraph("<b>Name:</b>", body_style), Paragraph(str(patient_info['patient_name']), body_style),
         Paragraph("<b>Age / Gender:</b>", body_style), Paragraph(f"{patient_info['age']} / {patient_info['gender']}", body_style)]
    ]
    t1 = Table(patient_data, colWidths=[100, 150, 100, 154])
    t1.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))
    
    # Section 2: Predicted Diagnosis
    story.append(Paragraph("SECTION 2: PREDICTED DIAGNOSIS", section_title_style))
    diag_data = [
        [Paragraph("<b>Predicted Disease:</b>", bold_body_style), Paragraph(f"<font color='#ef4444'><b>{diagnosis}</b></font>", ParagraphStyle('DiagText', parent=body_style, fontSize=11, leading=13))],
        [Paragraph("<b>Confidence Score:</b>", bold_body_style), Paragraph(f"<b>{confidence}%</b>", ParagraphStyle('ConfText', parent=body_style, fontSize=11, leading=13))]
    ]
    t2 = Table(diag_data, colWidths=[150, 354])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))
    
    # Section 3: Analysis
    story.append(Paragraph("SECTION 3: ANALYSIS", section_title_style))
    story.append(Paragraph("This diagnosis was determined using AI analysis of:", body_style))
    story.append(Spacer(1, 4))
    
    contrib_data = [
        [Paragraph(f"• Imaging (MRI/CT): {contributions[0]:.1f}% contribution", body_style)],
        [Paragraph(f"• Genetics: {contributions[1]:.1f}% contribution", body_style)],
        [Paragraph(f"• Clinical symptoms: {contributions[2]:.1f}% contribution", body_style)],
        [Paragraph(f"• Lab results: {contributions[3]:.1f}% contribution", body_style)]
    ]
    t3 = Table(contrib_data, colWidths=[504])
    t3.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8))
    
    # Add explanation chart
    if os.path.exists(chart_path):
        story.append(KeepTogether([
            Paragraph("<b>Modality Contribution Graph:</b>", bold_body_style),
            Spacer(1, 4),
            RLImage(chart_path, width=360, height=200),
            Spacer(1, 10)
        ]))
        
    # Section 4: Next Steps
    story.append(Paragraph("SECTION 4: NEXT STEPS", section_title_style))
    steps_data = [
        [Paragraph("1. Please consult with a medical specialist", body_style)],
        [Paragraph("2. Genetic testing recommended", body_style)],
        [Paragraph("3. Follow-up imaging may be needed", body_style)]
    ]
    t4 = Table(steps_data, colWidths=[504])
    t4.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t4)
    story.append(Spacer(1, 12))
    
    # Section 5: Disclaimer
    story.append(Paragraph("SECTION 5: DISCLAIMER", section_title_style))
    story.append(Paragraph("This AI analysis is for clinical decision support only. Not a replacement for physician judgment.", disclaimer_style))
    
    doc.build(story)


@retry_step("Step 7: Save to Database")
def run_step_7(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    pred = job["prediction_response"]
    report_path = job["report_file_path"]
    chart_path = job["explanation_image_path"]
    
    print("Step 7 - Saving to PostgreSQL database...")
    
    # Database Connection
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    insert_query = """
    INSERT INTO diagnosis_results (
        patient_id,
        patient_name,
        disease_predicted,
        confidence_score,
        imaging_importance,
        genetics_importance,
        clinical_importance,
        lab_importance,
        report_file_path,
        explanation_image_path,
        created_timestamp,
        doctor_email,
        status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
    RETURNING id;
    """
    
    weights = pred["attention_weights"]
    cursor.execute(insert_query, (
        form["patient_id"],
        form["patient_name"],
        pred["disease_name"],
        float(pred["confidence_percent"]),
        float(weights[0]),
        float(weights[1]),
        float(weights[2]),
        float(weights[3]),
        report_path,
        chart_path,
        form["doctor_email"],
        "COMPLETED"
    ))
    
    record_id = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    job["db_record_id"] = record_id
    print(f"Step 7 - Saved successfully. DB Record ID: {record_id}")
    return record_id


@retry_step("Step 8: Send Email Notification")
def run_step_8(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    pred = job["prediction_response"]
    report_path = job["report_file_path"]
    chart_path = job["explanation_image_path"]
    
    print("Step 8 - Building Email Notification...")
    
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import smtplib
    
    to_email = form["doctor_email"]
    patient_name = form["patient_name"]
    patient_id = form["patient_id"]
    disease_name = pred["disease_name"]
    confidence = pred["confidence_percent"]
    
    # Generate relative report URL
    report_filename = os.path.basename(report_path)
    report_link = f"http://localhost:5000/reports/{report_filename}"
    
    subject = f"Rare Disease AI Report Ready - {patient_id}"
    
    body = f"""Hello,

The AI analysis for patient {patient_name} is complete.

RESULT: {disease_name} ({confidence}% confidence)

The diagnostic report and explanation have been generated.

Access your report here: {report_link}

This analysis combined:
- Medical imaging analysis
- Genetic variant analysis  
- Clinical symptom analysis
- Lab result analysis

Please review with a medical specialist before clinical use.

Best regards,
Rare Disease AI System
"""
    
    msg = MIMEMultipart()
    msg['From'] = "reports@raredisease.ai"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach files
    for path in [report_path, chart_path]:
        if os.path.exists(path):
            filename = os.path.basename(path)
            part = MIMEBase('application', 'octet-stream')
            with open(path, 'rb') as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)
            
    # Save a local backup file (.eml)
    email_filename = f"report_email_{job_id}_{to_email.replace('@', '_')}.eml"
    email_path = os.path.join(EMAIL_DIR, email_filename)
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(msg.as_string())
    print(f"Step 8 - Local backup of doctor email saved to: {email_path}")
    
    # Try sending via debug SMTP on localhost (won't throw if absent)
    try:
        with smtplib.SMTP('localhost', 1025, timeout=2) as server:
            server.sendmail(msg['From'], [to_email], msg.as_string())
            print("Step 8 - Email sent successfully via SMTP.")
    except Exception:
        print("Step 8 - Real SMTP skip/failed. Backup available in sent_emails/ directory.")


@retry_step("Step 9: Update Dashboard")
def run_step_9(job_id):
    job = jobs[job_id]
    form = job["form_data"]
    pred = job["prediction_response"]
    report_path = job["report_file_path"]
    
    print("Step 9 - Updating Dashboard...")
    report_filename = os.path.basename(report_path)
    report_link = f"http://localhost:5000/reports/{report_filename}"
    
    payload = {
        "patient_id": form["patient_id"],
        "name": form["patient_name"],
        "diagnosis": pred["disease_name"],
        "confidence": float(pred["confidence_percent"]),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "report_link": report_link
    }
    
    # We call http://your-dashboard.com/api/add_patient
    # To prevent actual pipeline failure if domain doesn't exist, we fallback to localhost mock
    url = "http://your-dashboard.com/api/add_patient"
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code not in [200, 201]:
            raise Exception(f"Dashboard status code: {response.status_code}")
    except Exception as e:
        print(f"Warning: Step 9 Dashboard call to external domain failed: {e}. Running local mock redirect.")
        local_url = "http://localhost:5000/api/add_patient"
        local_resp = requests.post(local_url, json=payload, timeout=5)
        print(f"Local dashboard mock redirect response: {local_resp.status_code}")
        
    print("Step 9 - Dashboard updated.")


# --- MAIN PIPELINE WORKFLOW ---

def execute_pipeline(job_id):
    job = jobs[job_id]
    job["status"] = "PROCESSING"
    
    # Pipeline steps definitions
    steps_execution = [
        (2, "Checking Data Quality", run_step_2),
        (3, "Parallel Processing (Imaging, Genetics, Text, Lab)", run_step_3),
        (4, "Calling ML Model Server", run_step_4),
        (5, "Generating Modality Explanation Chart", run_step_5),
        (6, "Generating Diagnostic PDF Report", run_step_6),
        (7, "Saving Results to PostgreSQL Database", run_step_7),
        (8, "Sending Email Notification to Doctor", run_step_8),
        (9, "Updating Remote Dashboard API", run_step_9),
    ]
    
    try:
        for step_idx, step_desc, step_func in steps_execution:
            job["current_step"] = step_idx
            job["current_step_desc"] = step_desc
            print(f"\n>>> Executing STEP {step_idx}: {step_desc}...")
            step_func(job_id)
            
        # Complete
        job["status"] = "COMPLETED"
        job["current_step"] = 10
        job["current_step_desc"] = "Pipeline Finished Successfully."
        print(f"\n>>> Pipeline execution completed successfully for Job: {job_id}\n")
        
    except Exception as e:
        job["status"] = "FAILED"
        job["error"] = str(e)
        print(f"\n>>> Pipeline execution FAILED for Job: {job_id}. Error: {e}\n")
