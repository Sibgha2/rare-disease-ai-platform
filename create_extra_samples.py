import os
import numpy as np
import pandas as pd

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_data"))

def create_mock_dicom(file_path, patient_name, patient_id):
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    print(f"Creating sample DICOM at: {file_path}...")
    
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7'
    file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8'
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    
    ds = FileDataset(file_path, {}, file_meta=file_meta)
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.Modality = "CT"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.8"
    ds.StudyInstanceUID = "1.2.3.4.5.6.9"
    ds.FrameOfReferenceUID = "1.2.3.4.5.6.10"
    
    pixel_array = np.zeros((256, 256), dtype=np.uint16)
    xx, yy = np.meshgrid(np.arange(256), np.arange(256))
    circle = (xx - 128)**2 + (yy - 128)**2 < 80**2
    pixel_array[circle] = 1000
    pixel_array += np.random.randint(0, 40, (256, 256), dtype=np.uint16)
    
    ds.PixelData = pixel_array.tobytes()
    ds.Rows, ds.Columns = pixel_array.shape
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.PhotometricInterpretation = "MONOCHROME2"
    
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    ds.save_as(file_path)

def generate_cystic_fibrosis():
    cf_dir = os.path.join(SAMPLE_DIR, "cystic_fibrosis")
    os.makedirs(cf_dir, exist_ok=True)
    
    create_mock_dicom(os.path.join(cf_dir, "chest_ct.dcm"), "Claire^Fibrosis", "PT-1002")
    
    # Genetics
    df_gen = pd.DataFrame({
        "gene": ["CFTR", "TGFB1", "DCTN4", "SCNN1G"],
        "mutation": ["deltaF508", "promoter_variant", "missense", "nonsense"],
        "interaction_partner": ["SLC9A3", "SMAD3", "DYNC1H1", "SCNN1A"]
    })
    df_gen.to_csv(os.path.join(cf_dir, "cftr_mutation.csv"), index=False)
    
    # Clinical Notes
    notes = """CLINICAL NOTE
Patient is a 12-year-old female presenting with chronic cough, thick sputum production, and failure to thrive.
History of recurrent respiratory infections (Pseudomonas colonization noted).
Impression: Suspected Cystic Fibrosis. Sweat chloride test ordered.
"""
    with open(os.path.join(cf_dir, "clinical_notes_cf.txt"), "w") as f:
        f.write(notes)
        
    # Labs
    df_lab = pd.DataFrame({
        "test_name": ["Sweat Chloride", "Sputum Culture", "Sodium", "Chloride"],
        "value": [75.0, 1.0, 138.0, 108.0],
        "unit": ["mmol/L", "pos/neg", "mmol/L", "mmol/L"],
        "reference_range": ["0-30", "0-0", "135-145", "96-106"]
    })
    df_lab.to_csv(os.path.join(cf_dir, "chemistry_panel.csv"), index=False)

def generate_als():
    als_dir = os.path.join(SAMPLE_DIR, "als")
    os.makedirs(als_dir, exist_ok=True)
    
    create_mock_dicom(os.path.join(als_dir, "spine_mri.dcm"), "Arthur^Sclerosis", "PT-2041")
    
    # Genetics
    df_gen = pd.DataFrame({
        "gene": ["SOD1", "C9orf72", "TARDBP", "FUS"],
        "mutation": ["missense_A4V", "hexanucleotide_repeat", "missense", "splice_site"],
        "interaction_partner": ["CCS", "WDR26", "hnRNP", "U1_snRNP"]
    })
    df_gen.to_csv(os.path.join(als_dir, "sod1_mutation.csv"), index=False)
    
    # Clinical Notes
    notes = """CLINICAL NOTE
Patient is a 55-year-old male presenting with progressive weakness in right hand, slurred speech, and muscle fasciculations.
EMG shows widespread denervation.
Impression: Suspected Amyotrophic Lateral Sclerosis (ALS).
"""
    with open(os.path.join(als_dir, "clinical_notes_als.txt"), "w") as f:
        f.write(notes)
        
    # Labs
    df_lab = pd.DataFrame({
        "test_name": ["Creatine Kinase", "Serum Neurofilament Light", "Alanine Aminotransferase", "Aspartate Aminotransferase"],
        "value": [320.0, 85.0, 42.0, 38.0],
        "unit": ["U/L", "pg/mL", "U/L", "U/L"],
        "reference_range": ["39-308", "5-20", "7-56", "10-40"]
    })
    df_lab.to_csv(os.path.join(als_dir, "motor_neuron_labs.csv"), index=False)

def generate_marfan():
    marfan_dir = os.path.join(SAMPLE_DIR, "marfan_syndrome")
    os.makedirs(marfan_dir, exist_ok=True)
    
    create_mock_dicom(os.path.join(marfan_dir, "aortic_ultrasound.dcm"), "Mark^Syndrome", "PT-4409")
    
    # Genetics
    df_gen = pd.DataFrame({
        "gene": ["FBN1", "TGFBR1", "TGFBR2", "ACTA2"],
        "mutation": ["missense_C1039Y", "missense", "truncation", "missense"],
        "interaction_partner": ["TGFB1", "TGFB1", "TGFB1", "MYH11"]
    })
    df_gen.to_csv(os.path.join(marfan_dir, "fbn1_mutation.csv"), index=False)
    
    # Clinical Notes
    notes = """CLINICAL NOTE
Patient is a 24-year-old male presenting with joint hypermobility, tall stature, arm span exceeding height, and chest wall deformity.
Echocardiogram indicates root dilation.
Impression: Suspected Marfan Syndrome.
"""
    with open(os.path.join(marfan_dir, "clinical_notes_marfan.txt"), "w") as f:
        f.write(notes)
        
    # Labs
    df_lab = pd.DataFrame({
        "test_name": ["TGF-beta 1 level", "Homocysteine", "Calcium", "Serum Phosphorus"],
        "value": [4.8, 8.2, 9.4, 3.4],
        "unit": ["ng/mL", "umol/L", "mg/dL", "mg/dL"],
        "reference_range": ["1.0-4.0", "4.0-15.0", "8.5-10.2", "2.5-4.5"]
    })
    df_lab.to_csv(os.path.join(marfan_dir, "connective_tissue_labs.csv"), index=False)

if __name__ == "__main__":
    generate_cystic_fibrosis()
    generate_als()
    generate_marfan()
    print("\nExtra sample packages generated successfully in sample_data/ subdirectories:\n")
    print("- cystic_fibrosis/")
    print("- als/")
    print("- marfan_syndrome/")
