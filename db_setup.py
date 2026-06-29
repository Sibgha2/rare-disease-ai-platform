import os
import subprocess
import time
import sys

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "db_data"))
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "db_log.log"))
ANACONDA_BIN = r"C:\Users\sibgh\anaconda3\Library\bin"
INITDB = os.path.join(ANACONDA_BIN, "initdb.exe")
PG_CTL = os.path.join(ANACONDA_BIN, "pg_ctl.exe")

def is_db_installed():
    return os.path.exists(INITDB)

def init_db():
    if not is_db_installed():
        print("PostgreSQL server binaries not found in Anaconda path.")
        return False
        
    if not os.path.exists(DB_DIR):
        print(f"Initializing database cluster in {DB_DIR}...")
        os.makedirs(DB_DIR, exist_ok=True)
        # Using C locale and UTF-8 encoding
        cmd = [INITDB, "-D", DB_DIR, "-U", "postgres", "--locale=C", "-E", "UTF8"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error running initdb: {res.stderr}")
            return False
        print("Database cluster initialized successfully.")
    else:
        print("Database cluster already exists.")
    return True

def start_db():
    if not is_db_installed():
        print("PostgreSQL server binaries not found in Anaconda path.")
        return False

    print("Starting PostgreSQL server...")
    # pg_ctl start runs the server in the background.
    # We specify the log file using -l option.
    cmd = [PG_CTL, "-D", DB_DIR, "-l", LOG_FILE, "start"]
    try:
        # Use subprocess.Popen to launch pg_ctl without blocking
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000200) # CREATE_NEW_PROCESS_GROUP
    except Exception as e:
        print(f"Error starting database: {e}")
        return False
    
    # Wait for startup and check port connection
    print("Waiting 5 seconds for PostgreSQL server to start...")
    time.sleep(5)
    return True

def stop_db():
    if not is_db_installed():
        return
    print("Stopping PostgreSQL server...")
    cmd = [PG_CTL, "-D", DB_DIR, "stop"]
    subprocess.run(cmd, capture_output=True, text=True)
    print("PostgreSQL server stopped.")

def setup_tables():
    print("Setting up database tables...")
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to default postgres database to verify/create our tables
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create table diagnosis_results if it does not exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS diagnosis_results (
            id SERIAL PRIMARY KEY,
            patient_id VARCHAR(100) NOT NULL,
            patient_name VARCHAR(255) NOT NULL,
            disease_predicted VARCHAR(255) NOT NULL,
            confidence_score DOUBLE PRECISION NOT NULL,
            imaging_importance DOUBLE PRECISION NOT NULL,
            genetics_importance DOUBLE PRECISION NOT NULL,
            clinical_importance DOUBLE PRECISION NOT NULL,
            lab_importance DOUBLE PRECISION NOT NULL,
            report_file_path TEXT NOT NULL,
            explanation_image_path TEXT NOT NULL,
            created_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            doctor_email VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            trigger_type VARCHAR(50) NOT NULL DEFAULT 'direct_clinician',
            risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            audit_log TEXT NOT NULL DEFAULT '',
            is_encrypted BOOLEAN NOT NULL DEFAULT FALSE
        );
        """
        cursor.execute(create_table_query)
        
        # Ensure columns exist if table was already created
        alter_queries = [
            "ALTER TABLE diagnosis_results ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(50) NOT NULL DEFAULT 'direct_clinician';",
            "ALTER TABLE diagnosis_results ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM';",
            "ALTER TABLE diagnosis_results ADD COLUMN IF NOT EXISTS audit_log TEXT NOT NULL DEFAULT '';",
            "ALTER TABLE diagnosis_results ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN NOT NULL DEFAULT FALSE;"
        ]
        for query in alter_queries:
            cursor.execute(query)
            
        print("Table 'diagnosis_results' verified/created and updated successfully with RareGuard schema.")
        
        # Verify structure
        cursor.execute("SELECT COUNT(*) FROM diagnosis_results;")
        count = cursor.fetchone()[0]
        print(f"Current record count in diagnosis_results: {count}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting up tables: {e}")
        return False

if __name__ == "__main__":
    if not is_db_installed():
        print("Error: PostgreSQL server binaries are missing. Please make sure Conda installation finishes.")
        sys.exit(1)
    
    if init_db():
        if start_db():
            setup_tables()
