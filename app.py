import os
import json
import uuid
import secrets
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g

from werkzeug.utils import secure_filename

# Import pipeline components (pipeline_annotated re-exports from pipeline + adds annotation support)
try:
    from pipeline_annotated import execute_pipeline, jobs, UPLOAD_DIR, REPORT_DIR, CHART_DIR, EMAIL_DIR
except ImportError:
    from pipeline import execute_pipeline, jobs, UPLOAD_DIR, REPORT_DIR, CHART_DIR, EMAIL_DIR

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANNOTATION_DIR = os.path.join(BASE_DIR, "annotations")
DOCTORS_FILE = os.path.join(BASE_DIR, "static", "doctors.json")
os.makedirs(ANNOTATION_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.secret_key = os.environ.get('SECRET_KEY', 'rareguard-ai-secret-dev-key-2026')

# In-memory active sessions: token -> user dict
active_tokens = {}

# ─────────────────────────────────────────────
#  DOCTOR REGISTRY HELPERS
# ─────────────────────────────────────────────

def load_doctors():
    if os.path.exists(DOCTORS_FILE):
        with open(DOCTORS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "superadmin": {
            "email": "admin@raredisease.ai",
            "password": "Admin@123",
            "role": "superadmin",
            "name": "Super Admin"
        },
        "doctors": []
    }

def save_doctors(data):
    with open(DOCTORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────────
#  AUTH DECORATORS
# ─────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not token or token not in active_tokens:
            return jsonify({"error": "Unauthorized — please login"}), 401
        g.current_user = active_tokens[token]
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not token or token not in active_tokens:
            return jsonify({"error": "Unauthorized"}), 401
        user = active_tokens[token]
        if user.get('role') != 'superadmin':
            return jsonify({"error": "Forbidden — SuperAdmin access required"}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
#  MOCK ML PREDICTION LOGIC
# ─────────────────────────────────────────────

def mock_prediction_logic(suspected_condition):
    condition = str(suspected_condition).lower().strip()
    if "huntington" in condition:
        disease = "Huntington's Disease"
        explanation = (
            "High number of CAG trinucleotide repeats detected on chromosome 4 in the HTT gene. "
            "Bilateral caudate nucleus atrophy visible on MRI with characteristic 'box-car' ventricle pattern. "
            "Genetic analysis confirms autosomal dominant inheritance pattern with 42 CAG repeats (pathogenic threshold: >36)."
        )
        weights = [35.0, 45.0, 10.0, 10.0]
        findings = {
            "imaging": "Bilateral caudate atrophy, enlarged lateral ventricles, reduced putamen volume",
            "genetics": "HTT gene mutation: 42 CAG repeats (Pathogenic). Penetrance: Full",
            "clinical": "Progressive chorea, cognitive decline, psychiatric symptoms noted",
            "labs": "Elevated CSF neurofilament light chain; normal routine metabolic panel"
        }
    elif "cystic" in condition or "fibrosis" in condition:
        disease = "Cystic Fibrosis"
        explanation = (
            "Homozygous ΔF508 mutation in the CFTR gene detected on chromosome 7. "
            "Clinical notes show persistent respiratory infection with P. aeruginosa. "
            "Elevated sweat chloride (102 mEq/L) confirms CFTR dysfunction. Bilateral bronchiectasis on imaging."
        )
        weights = [15.0, 50.0, 15.0, 20.0]
        findings = {
            "imaging": "Bilateral bronchiectasis, mucus plugging in right upper lobe, air trapping",
            "genetics": "CFTR: ΔF508/ΔF508 (homozygous). Class II mutation — protein misfolding",
            "clinical": "FEV1 62% predicted, chronic P. aeruginosa colonization, nutritional deficiency",
            "labs": "Sweat Cl⁻: 102 mEq/L (>60 diagnostic). Elevated faecal elastase: 85 µg/g"
        }
    elif "als" in condition or "lateral sclerosis" in condition:
        disease = "Amyotrophic Lateral Sclerosis (ALS)"
        explanation = (
            "Loss of upper and lower motor neurons in the anterior horn of the spinal cord observed. "
            "SOD1 gene variant of uncertain significance detected. EMG shows widespread denervation. "
            "Clinical muscle weakness progressing per El Escorial criteria — Definite ALS."
        )
        weights = [30.0, 20.0, 30.0, 20.0]
        findings = {
            "imaging": "Corticospinal tract T2 hyperintensity, motor cortex thinning",
            "genetics": "SOD1 p.Ala5Val variant (likely pathogenic). FUS, TDP-43: negative",
            "clinical": "Upper + lower motor neuron signs. ALSFRS-R: 34/48 (declining 1.2/month)",
            "labs": "Elevated serum neurofilament light: 78 pg/mL (>35 abnormal). CK: 312 U/L"
        }
    elif "marfan" in condition:
        disease = "Marfan Syndrome"
        explanation = (
            "Pathogenic variant in FBN1 gene (c.5788G>A) on chromosome 15. "
            "MRI shows aortic root diameter 4.6 cm (Z-score +3.8) with mild mitral valve prolapse. "
            "Clinical markers include tall stature, arachnodactyly, and positive wrist & thumb signs."
        )
        weights = [40.0, 35.0, 15.0, 10.0]
        findings = {
            "imaging": "Aortic root dilation: 4.6 cm, mitral valve prolapse, lens dislocation (ectopia lentis)",
            "genetics": "FBN1 c.5788G>A (p.Gly1930Arg) — Class 5 Pathogenic. de novo confirmed",
            "clinical": "Arm span:height ratio 1.09, positive Steinberg thumb sign, high palate",
            "labs": "TGF-β pathway biomarkers elevated. Fibrillin-1 ELISA: 40% of normal"
        }
    else:
        disease = "Fabry Disease"
        explanation = (
            "Hemizygous pathogenic variant in GLA gene (c.680G>A, p.Arg227Gln) confirmed. "
            "Alpha-galactosidase A enzyme activity: 2% of normal (severely reduced). "
            "MRI shows white matter lesions in posterior fossa. Renal biopsy shows GL-3 inclusions."
        )
        weights = [25.0, 35.0, 20.0, 20.0]
        findings = {
            "imaging": "White matter hyperintensities in pulvinar & posterior fossa, T1 'pulvinar sign'",
            "genetics": "GLA c.680G>A (p.Arg227Gln) — hemizygous. Alpha-Gal A activity: 2%",
            "clinical": "Neuropathic pain (burning), angiokeratoma, hypohidrosis, corneal whorling",
            "labs": "Lyso-Gb3: 120 nmol/L (>10 diagnostic). Creatinine: 1.8 mg/dL (renal impairment)"
        }

    return {
        "disease_name": disease,
        "confidence_percent": 93.4,
        "attention_weights": weights,
        "explanation": explanation,
        "modality_findings": findings
    }

# ─────────────────────────────────────────────
#  STATIC ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory("static", "index.html")

@app.route('/login')
@app.route('/login.html')
def login_page():
    return send_from_directory("static", "login.html")

@app.route('/admin')
@app.route('/admin.html')
def admin_page():
    return send_from_directory("static", "admin.html")

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory("static", path)

@app.route('/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory(REPORT_DIR, filename)

@app.route('/explanations/<path:filename>')
def serve_explanation(filename):
    return send_from_directory(CHART_DIR, filename)

@app.route('/annotations/<path:filename>')
def serve_annotation(filename):
    return send_from_directory(ANNOTATION_DIR, filename)

# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload"}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    doctors_data = load_doctors()

    # Check superadmin
    superadmin = doctors_data.get('superadmin', {})
    if email == superadmin.get('email', '').lower() and password == superadmin.get('password', ''):
        token = secrets.token_hex(32)
        user_info = {
            'email': email,
            'name': superadmin.get('name', 'Super Admin'),
            'role': 'superadmin',
            'specialization': 'System Administrator',
            'hospital': 'RareDiseaseAI Platform'
        }
        active_tokens[token] = user_info
        return jsonify({'token': token, **user_info})

    # Check registered doctors
    for doc in doctors_data.get('doctors', []):
        if doc.get('email', '').lower() == email and doc.get('password', '') == password:
            token = secrets.token_hex(32)
            user_info = {
                'email': email,
                'name': doc.get('name', 'Dr. Unknown'),
                'role': 'doctor',
                'specialization': doc.get('specialization', ''),
                'hospital': doc.get('hospital', '')
            }
            active_tokens[token] = user_info
            return jsonify({'token': token, **user_info})

    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    active_tokens.pop(token, None)
    return jsonify({"status": "logged out"})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def auth_me():
    return jsonify(g.current_user)

# ─────────────────────────────────────────────
#  SUPERADMIN ROUTES
# ─────────────────────────────────────────────

@app.route('/api/admin/doctors', methods=['GET'])
@require_admin
def list_doctors():
    data = load_doctors()
    safe_doctors = [{k: v for k, v in d.items() if k != 'password'}
                    for d in data.get('doctors', [])]
    return jsonify(safe_doctors)

@app.route('/api/admin/register-doctor', methods=['POST'])
@require_admin
def register_doctor():
    data = request.get_json()
    required = ['name', 'email', 'password', 'specialization', 'hospital']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'error': f'Missing required field: {field}'}), 400

    doctors_data = load_doctors()
    new_email = data['email'].strip().lower()

    for doc in doctors_data.get('doctors', []):
        if doc.get('email', '').lower() == new_email:
            return jsonify({'error': 'A doctor with this email already exists'}), 409

    new_doctor = {
        'name': data['name'].strip(),
        'email': new_email,
        'password': data['password'],
        'specialization': data['specialization'].strip(),
        'hospital': data['hospital'].strip(),
        'role': 'doctor',
        'created_at': datetime.now().isoformat()
    }
    doctors_data['doctors'].append(new_doctor)
    save_doctors(doctors_data)

    safe_doc = {k: v for k, v in new_doctor.items() if k != 'password'}
    return jsonify(safe_doc), 201

@app.route('/api/admin/doctors/<path:email>', methods=['DELETE'])
@require_admin
def delete_doctor(email):
    doctors_data = load_doctors()
    original = len(doctors_data.get('doctors', []))
    doctors_data['doctors'] = [
        d for d in doctors_data.get('doctors', [])
        if d.get('email', '').lower() != email.lower()
    ]
    if len(doctors_data['doctors']) == original:
        return jsonify({'error': 'Doctor not found'}), 404
    save_doctors(doctors_data)
    return jsonify({'status': 'deleted'})

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    doctors_data = load_doctors()
    total_doctors = len(doctors_data.get('doctors', []))
    total_jobs = len(jobs)
    completed = sum(1 for j in jobs.values() if j.get('status') == 'COMPLETED')
    failed = sum(1 for j in jobs.values() if j.get('status') == 'FAILED')
    return jsonify({
        'total_doctors': total_doctors,
        'total_jobs': total_jobs,
        'completed_jobs': completed,
        'failed_jobs': failed,
        'active_sessions': len(active_tokens)
    })

# ─────────────────────────────────────────────
#  PATIENT HISTORY
# ─────────────────────────────────────────────

@app.route('/api/patients/history', methods=['GET'])
@require_auth
def patients_history():
    history = []
    for job_id, job in jobs.items():
        if job.get('status') in ['COMPLETED', 'FAILED']:
            pred = job.get('prediction_response') or {}
            entry = {
                'job_id': job_id,
                'status': job['status'],
                'patient_id': job.get('form_data', {}).get('patient_id', '—'),
                'patient_name': job.get('form_data', {}).get('patient_name', '—'),
                'age': job.get('form_data', {}).get('age', '—'),
                'gender': job.get('form_data', {}).get('gender', '—'),
                'disease': pred.get('disease_name'),
                'confidence': pred.get('confidence_percent'),
                'doctor_email': job.get('form_data', {}).get('doctor_email', '—'),
                'report_url': f"/reports/report_{job_id}.pdf" if job['status'] == 'COMPLETED' else None,
                'annotation_url': f"/annotations/annotated_{job_id}.png" if job['status'] == 'COMPLETED' else None,
                'chart_url': f"/explanations/chart_{job_id}.png" if job['status'] == 'COMPLETED' else None,
            }
            history.append(entry)
    return jsonify(sorted(history, key=lambda x: x['job_id'], reverse=True))

# ─────────────────────────────────────────────
#  CORE PIPELINE ROUTES
# ─────────────────────────────────────────────

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    resp = {
        "job_id": job_id,
        "status": job["status"],
        "current_step": job["current_step"],
        "current_step_desc": job["current_step_desc"],
        "error": job.get("error")
    }

    if job["status"] == "COMPLETED":
        resp["db_record_id"] = job.get("db_record_id")
        resp["report_url"] = f"/reports/report_{job_id}.pdf"
        resp["explanation_chart_url"] = f"/explanations/chart_{job_id}.png"
        resp["annotation_url"] = f"/annotations/annotated_{job_id}.png"
        resp["prediction"] = job.get("prediction_response")
        resp["risk_level"] = job.get("risk_level", "MEDIUM")
        resp["trigger_type"] = job.get("form_data", {}).get("trigger_type", "direct_clinician")
        resp["surveillance_notes"] = job.get("surveillance_notes", "")
        resp["audit_trail"] = job.get("audit_trail", [])

    return jsonify(resp)

@app.route('/api/run-pipeline', methods=['POST'])
def run_pipeline():
    try:
        patient_id = request.form.get("patient_id")
        patient_name = request.form.get("patient_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        medical_condition_suspected = request.form.get("medical_condition_suspected")
        doctor_email = request.form.get("doctor_email")
        trigger_type = request.form.get("trigger_type", "direct_clinician")

        saved_files = {}
        job_id = str(uuid.uuid4())
        job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
        os.makedirs(job_upload_dir, exist_ok=True)

        for key in ["imaging_file", "genetic_data_file", "clinical_notes_file", "lab_results_file"]:
            file = request.files.get(key)
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                save_path = os.path.join(job_upload_dir, filename)
                file.save(save_path)
                saved_files[key] = save_path

        jobs[job_id] = {
            "status": "PENDING",
            "current_step": 1,
            "current_step_desc": "Patient data form validation completed.",
            "form_data": {
                "patient_id": patient_id,
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "medical_condition_suspected": medical_condition_suspected,
                "doctor_email": doctor_email,
                "trigger_type": trigger_type
            },
            "files": saved_files,
            "error": None,
            "audit_trail": []
        }

        thread = threading.Thread(target=execute_pipeline, args=(job_id,))
        thread.daemon = True
        thread.start()

        return jsonify({"job_id": job_id, "status": "PENDING"}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ─────────────────────────────────────────────
#  MOCK ML MODEL & DASHBOARD
# ─────────────────────────────────────────────

@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json()
    if not data or "patient_id" not in data:
        return jsonify({"error": "Missing patient_id in payload"}), 400

    patient_id = data["patient_id"]
    suspected_condition = "Fabry Disease"
    for job in jobs.values():
        if job.get("form_data", {}).get("patient_id") == patient_id:
            suspected_condition = job["form_data"].get("medical_condition_suspected", "")
            break

    return jsonify(mock_prediction_logic(suspected_condition))

@app.route('/api/add_patient', methods=['POST'])
def api_add_patient():
    data = request.get_json()
    print(f"\n[Mock Dashboard] Received patient update API call: {data}\n")
    return jsonify({"status": "success", "message": "Patient dashboard updated successfully"}), 200

# ─────────────────────────────────────────────
#  CORS
# ─────────────────────────────────────────────

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return jsonify({}), 200

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    from db_setup import init_db, start_db, setup_tables
    print("Ensuring PostgreSQL database is running...")
    if init_db():
        if start_db():
            setup_tables()

    print("Launching RareGuard AI Platform on http://localhost:5000...")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
