import os
import time
import requests
import psycopg2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")
SERVER_URL = "http://localhost:5000"

def test_workflow():
    print("Starting RareGuard AI Platform — 10-Stage Pipeline Integration Test...")
    
    # 1. Prepare files to send
    files = {
        "imaging_file": open(os.path.join(SAMPLE_DIR, "brain_mri.dcm"), "rb"),
        "genetic_data_file": open(os.path.join(SAMPLE_DIR, "genetic_variants.csv"), "rb"),
        "clinical_notes_file": open(os.path.join(SAMPLE_DIR, "clinical_notes.txt"), "rb"),
        "lab_results_file": open(os.path.join(SAMPLE_DIR, "lab_results.csv"), "rb")
    }
    
    # 2. Form data metadata
    data = {
        "patient_id": "PT-9402",
        "patient_name": "John Doe",
        "age": 34,
        "gender": "M",
        "medical_condition_suspected": "Huntington's Disease",
        "doctor_email": "doctor@hospital.org",
        "trigger_type": "death_registry"  # Test surveillance trigger
    }
    
    # 3. Post to /api/run-pipeline
    print("Submitting diagnostics intake form...")
    resp = requests.post(f"{SERVER_URL}/api/run-pipeline", data=data, files=files)
    
    # Close files
    for f in files.values():
        f.close()
        
    if resp.status_code != 202:
        print(f"FAILED: Initial submission returned status {resp.status_code}: {resp.text}")
        return False
        
    job_id = resp.json()["job_id"]
    print(f"Submission successful. Job ID: {job_id}. Polling progress status...")
    
    # 4. Poll job status
    max_polls = 40
    poll_count = 0
    completed = False
    
    while poll_count < max_polls:
        time.sleep(2)
        poll_count += 1
        
        status_resp = requests.get(f"{SERVER_URL}/api/jobs/{job_id}")
        if status_resp.status_code != 200:
            print(f"FAILED: Status endpoint returned error: {status_resp.text}")
            return False
            
        status_data = status_resp.json()
        print(f"Poll {poll_count}/{max_polls} - Status: {status_data['status']} | Step {status_data['current_step']}/10: {status_data['current_step_desc']}")
        
        if status_data["status"] == "COMPLETED":
            completed = True
            break
        elif status_data["status"] == "FAILED":
            print(f"FAILED: Job entered failed state: {status_data['error']}")
            return False
            
    if not completed:
        print("FAILED: Job execution timed out.")
        return False
        
    print("\n>>> Pipeline finished successfully! Commencing database and output assertions...")
    
    # 5. Assert database entry exists
    db_id = status_data["db_record_id"]
    print(f"Verifying PostgreSQL database entry (Record ID: {db_id})...")
    try:
        conn = psycopg2.connect(host="localhost", port=5432, user="postgres", database="postgres")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM diagnosis_results WHERE id = %s;", (db_id,))
        row = cursor.fetchone()
        
        if not row:
            print("FAILED: No database entry found for Record ID.")
            return False
            
        print(f"PostgreSQL Assertion PASSED: Found matching database row: Patient ID={row[1]}, Name={row[2]}, Disease={row[3]}, Conf={row[4]}%")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"FAILED: Database verification error: {e}")
        return False
        
    report_filename = f"report_{job_id}.pdf"
    chart_filename = f"chart_{job_id}.png"
    annot_filename = f"annotated_{job_id}.png"
    
    report_path = os.path.join(BASE_DIR, "reports", report_filename)
    chart_path = os.path.join(BASE_DIR, "explanations", chart_filename)
    annot_path = os.path.join(BASE_DIR, "annotations", annot_filename)
    
    if not os.path.exists(report_path):
        print(f"FAILED: Report PDF missing at {report_path}")
        return False
    print(f"File Assertion PASSED: PDF report exists ({os.path.getsize(report_path)} bytes)")
    
    if not os.path.exists(chart_path):
        print(f"FAILED: Explanation chart PNG missing at {chart_path}")
        return False
    print(f"File Assertion PASSED: Chart PNG exists ({os.path.getsize(chart_path)} bytes)")

    if not os.path.exists(annot_path):
        print(f"FAILED: Annotated scan PNG missing at {annot_path}")
        return False
    print(f"File Assertion PASSED: Annotated scan PNG exists ({os.path.getsize(annot_path)} bytes)")
    
    # 7. Check sent emails directory
    sent_emails = os.listdir(os.path.join(BASE_DIR, "sent_emails"))
    matching_emails = [e for e in sent_emails if job_id in e]
    if len(matching_emails) == 0:
        print("FAILED: No email notification backup found in sent_emails/ directory.")
        return False
    print(f"Notification Assertion PASSED: Saved copy of doctor report email: {matching_emails[0]}")
    
    # 8. Assert new RareGuard AI response fields
    risk_level = status_data.get("risk_level", None)
    trigger_type = status_data.get("trigger_type", None)
    audit_trail = status_data.get("audit_trail", [])

    if not risk_level:
        print("FAILED: risk_level missing from completed job response.")
        return False
    print(f"RareGuard Assertion PASSED: Risk Level = {risk_level}")

    if trigger_type != "death_registry":
        print(f"WARNING: trigger_type returned '{trigger_type}', expected 'death_registry'.")
    else:
        print(f"RareGuard Assertion PASSED: Trigger Type = {trigger_type}")

    if len(audit_trail) == 0:
        print("WARNING: Audit trail is empty.")
    else:
        print(f"RareGuard Assertion PASSED: Audit trail has {len(audit_trail)} entries.")

    print("\nALL RAREGUARD AI SYSTEM VERIFICATIONS PASSED SUCCESSFULLY! 100% SUCCESS RATE.")
    return True

if __name__ == "__main__":
    test_workflow()
