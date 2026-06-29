import os
import numpy as np
import pandas as pd

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_data"))
os.makedirs(SAMPLE_DIR, exist_ok=True)

def create_dicom():
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    
    file_path = os.path.join(SAMPLE_DIR, "brain_mri.dcm")
    print(f"Creating sample DICOM at: {file_path}...")
    
    # Create file metadata dataset
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
    file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7'
    file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8'
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'  # Explicit VR Little Endian
    
    # Create main Dataset
    ds = FileDataset(file_path, {}, file_meta=file_meta)
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.PatientName = "Test^Patient"
    ds.PatientID = "PT-9402"
    ds.Modality = "CT"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.8"
    ds.StudyInstanceUID = "1.2.3.4.5.6.9"
    ds.FrameOfReferenceUID = "1.2.3.4.5.6.10"
    
    # Generate mock 256x256 pixel data (a simple circle representing a head cross-section)
    pixel_array = np.zeros((256, 256), dtype=np.uint16)
    xx, yy = np.meshgrid(np.arange(256), np.arange(256))
    circle = (xx - 128)**2 + (yy - 128)**2 < 80**2
    pixel_array[circle] = 1200
    
    # Add a mock brain-like inner mass
    brain = (xx - 128)**2 + (yy - 128)**2 < 65**2
    pixel_array[brain] = 600
    
    # Add random noise
    pixel_array += np.random.randint(0, 50, (256, 256), dtype=np.uint16)
    
    ds.PixelData = pixel_array.tobytes()
    ds.Rows, ds.Columns = pixel_array.shape
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    
    # Required for pydicom save
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    ds.save_as(file_path)
    print("DICOM file created.")

def create_genetics():
    file_path = os.path.join(SAMPLE_DIR, "genetic_variants.csv")
    print(f"Creating sample Genetics CSV at: {file_path}...")
    df = pd.DataFrame({
        "gene": ["HTT", "CFTR", "FBN1", "GLA", "SOD1"],
        "mutation": ["CAG_repeat_48", "deltaF508", "missense_C1039Y", "nonsense_W262X", "missense_A4V"],
        "interaction_partner": ["BDNF", "SLC9A3", "TGFBR1", "GLB1", "CCS"]
    })
    df.to_csv(file_path, index=False)
    print("Genetics file created.")

def create_clinical():
    file_path = os.path.join(SAMPLE_DIR, "clinical_notes.txt")
    print(f"Creating sample Clinical Notes TXT at: {file_path}...")
    notes = """CLINICAL NOTE - INTAKE ASSESSMENT
Patient is a 34-year-old male presenting with family history of neurological disorders.
Symptoms:
- Involuntary jerky movements (chorea) observed in upper extremities.
- Mild dysarthria and progressive balance issues.
- Patient and spouse report slight cognitive irritability and short-term memory lapses.
- No history of cardiorespiratory symptoms.
Clinical impression: Suspected Huntington's Disease. Recommending genetic sequence confirmation.
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(notes)
    print("Clinical notes created.")

def create_labs():
    file_path = os.path.join(SAMPLE_DIR, "lab_results.csv")
    print(f"Creating sample Lab Results CSV at: {file_path}...")
    df = pd.DataFrame({
        "test_name": ["Hemoglobin", "White Blood Cells", "Serum Creatinine", "Alanine Aminotransferase", "Sweat Chloride"],
        "value": [14.2, 7.5, 0.9, 28, 45],
        "unit": ["g/dL", "k/uL", "mg/dL", "U/L", "mmol/L"],
        "reference_range": ["13.8-17.2", "4.5-11.0", "0.6-1.2", "7-56", "0-30"]
    })
    df.to_csv(file_path, index=False)
    print("Lab results file created.")

if __name__ == "__main__":
    create_dicom()
    create_genetics()
    create_clinical()
    create_labs()
    print("\nAll sample files generated successfully in: sample_data/\n")
