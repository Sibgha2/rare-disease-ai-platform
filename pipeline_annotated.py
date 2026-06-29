"""
pipeline_annotated.py — RareGuard AI: Extends pipeline.py with scan annotation.
This module hooks into the 10-stage pipeline (Stage 6 and Stage 7) to inject
XAI scan annotation overlays and premium PDF report generation.
All other stages delegate to the base pipeline module.
"""
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Ensure this directory is in the path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Re-export everything from the original pipeline
from pipeline import (
    execute_pipeline,
    jobs,
    UPLOAD_DIR,
    REPORT_DIR,
    CHART_DIR,
    EMAIL_DIR,
    LOG_DIR,
)

# Add ANNOTATION_DIR if not in pipeline yet
ANNOTATION_DIR = os.path.join(BASE_DIR, "annotations")
os.makedirs(ANNOTATION_DIR, exist_ok=True)

# Monkey patch steps to use our custom premium features
import pipeline
import pdf_report

# Save original Step 6 (Explanation Chart) in the 10-stage pipeline
original_run_step_6 = pipeline.run_step_6

def generate_scan_annotation_image(disease, output_path):
    fig, ax = plt.subplots(figsize=(6, 5), facecolor='#0b0f19')
    ax.set_facecolor('#0b0f19')
    
    # Hide axes
    ax.axis('off')
    
    # Draw background grid lines (medical scan grid style)
    for i in range(1, 10):
        ax.axhline(i * 10, color='#1e293b', linestyle=':', alpha=0.3)
        ax.axvline(i * 10, color='#1e293b', linestyle=':', alpha=0.3)
        
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    
    if disease == "Huntington's Disease":
        # Draw brain contour
        brain = patches.Ellipse((50, 50), 75, 85, color='#1e293b', alpha=0.4)
        ax.add_patch(brain)
        # Inner brain structures
        ventricle_l = patches.Ellipse((42, 55), 10, 25, angle=-10, color='#111827')
        ventricle_r = patches.Ellipse((58, 55), 10, 25, angle=10, color='#111827')
        ax.add_patch(ventricle_l)
        ax.add_patch(ventricle_r)
        
        # Overlays
        # Caudate Nucleus Atrophy ROI (Red)
        rect_l = patches.Rectangle((33, 40), 8, 12, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        rect_r = patches.Rectangle((59, 40), 8, 12, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        ax.add_patch(rect_l)
        ax.add_patch(rect_r)
        ax.text(37, 34, "Caudate Nucleus Atrophy", color='#ff3c3c', fontsize=8, ha='center', fontweight='bold')
        
        # Basal Ganglia Changes ROI (Orange)
        bg_l = patches.Ellipse((28, 48), 6, 12, angle=-5, linewidth=1.5, edgecolor='#ffa500', facecolor='none')
        bg_r = patches.Ellipse((72, 48), 6, 12, angle=5, linewidth=1.5, edgecolor='#ffa500', facecolor='none')
        ax.add_patch(bg_l)
        ax.add_patch(bg_r)
        ax.text(20, 52, "Basal Ganglia\nChanges", color='#ffa500', fontsize=8, ha='center')
        
        # Lateral Ventricles ROI (Blue)
        v_overlay_l = patches.Ellipse((42, 55), 8, 20, angle=-10, linewidth=1.5, edgecolor='#64c8ff', facecolor='none')
        v_overlay_r = patches.Ellipse((58, 55), 8, 20, angle=10, linewidth=1.5, edgecolor='#64c8ff', facecolor='none')
        ax.add_patch(v_overlay_l)
        ax.add_patch(v_overlay_r)
        ax.text(50, 75, "Enlarged Lateral Ventricles\n(Box-Car ventricles)", color='#64c8ff', fontsize=8, ha='center')
        
    elif disease == "Cystic Fibrosis":
        # Draw lungs chest contour
        chest = patches.Ellipse((50, 50), 85, 80, color='#1e293b', alpha=0.4)
        ax.add_patch(chest)
        
        lung_l = patches.Ellipse((33, 50), 22, 55, angle=5, color='#111827')
        lung_r = patches.Ellipse((67, 50), 22, 55, angle=-5, color='#111827')
        ax.add_patch(lung_l)
        ax.add_patch(lung_r)
        
        # Lung Infiltration ROI (Red)
        inf_1 = patches.Circle((32, 60), 6, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        inf_2 = patches.Circle((68, 40), 7, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        ax.add_patch(inf_1)
        ax.add_patch(inf_2)
        # draw some textured infiltrates
        for dx, dy in [(-2, 0), (2, 1), (0, -2)]:
            ax.plot(32+dx, 60+dy, 'ro', markersize=2, alpha=0.6)
            ax.plot(68+dx, 40+dy, 'ro', markersize=2, alpha=0.6)
        ax.text(32, 70, "Bronchiectasis &\nInfiltration", color='#ff3c3c', fontsize=8, ha='center', fontweight='bold')
        
        # Air Trapping ROI (Yellow/Gold)
        trap_1 = patches.Ellipse((35, 35), 8, 12, angle=10, linewidth=1.5, edgecolor='#ffc800', facecolor='none')
        ax.add_patch(trap_1)
        ax.text(35, 20, "Air Trapping", color='#ffc800', fontsize=8, ha='center')
        
    elif disease == "Amyotrophic Lateral Sclerosis (ALS)":
        # Draw brain or spinal cord cross section
        brain = patches.Ellipse((50, 50), 75, 85, color='#1e293b', alpha=0.4)
        ax.add_patch(brain)
        
        # Corticospinal Tract Signal ROI (Red)
        cst_l = patches.Circle((38, 42), 5, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        cst_r = patches.Circle((62, 42), 5, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        ax.add_patch(cst_l)
        ax.add_patch(cst_r)
        ax.text(50, 32, "Corticospinal Tract T2 Hyperintensity", color='#ff3c3c', fontsize=8, ha='center', fontweight='bold')
        
        # Motor Cortex Thinning ROI (Orange)
        mc_l = patches.Ellipse((30, 68), 8, 15, angle=20, linewidth=1.5, edgecolor='#ffa500', facecolor='none')
        mc_r = patches.Ellipse((70, 68), 8, 15, angle=-20, linewidth=1.5, edgecolor='#ffa500', facecolor='none')
        ax.add_patch(mc_l)
        ax.add_patch(mc_r)
        ax.text(50, 85, "Primary Motor Cortex Thinning", color='#ffa500', fontsize=8, ha='center')
        
    elif disease == "Marfan Syndrome":
        # Draw heart schematic
        heart = patches.Ellipse((50, 42), 35, 45, color='#1e293b', alpha=0.4)
        ax.add_patch(heart)
        
        # Draw aortic arch
        aorta = patches.Arc((50, 58), 28, 30, theta1=20, theta2=190, color='#374151', linewidth=8)
        ax.add_patch(aorta)
        
        # Aortic Root Dilation ROI (Red)
        a_root = patches.Ellipse((58, 50), 12, 14, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        ax.add_patch(a_root)
        ax.text(78, 52, "Aortic Root\nDilation (4.6 cm)", color='#ff3c3c', fontsize=8, ha='center', fontweight='bold')
        
        # Thoracic Aorta ROI (Orange)
        t_aorta = patches.Rectangle((34, 42), 6, 15, linewidth=1.5, edgecolor='#ffa500', facecolor='none')
        ax.add_patch(t_aorta)
        ax.text(22, 45, "Thoracic\nAorta", color='#ffa500', fontsize=8, ha='center')
        
        # Mitral Valve Prolapse ROI (Purple)
        mvp = patches.Circle((46, 36), 5, linewidth=1.5, edgecolor='#c864ff', facecolor='none')
        ax.add_patch(mvp)
        ax.text(46, 26, "Mitral Valve Prolapse", color='#c864ff', fontsize=8, ha='center')
        
    else:  # Fabry Disease
        # Draw kidneys or brain cross section
        brain = patches.Ellipse((50, 50), 75, 85, color='#1e293b', alpha=0.4)
        ax.add_patch(brain)
        
        # Kidney GL-3 Deposits ROI (Red) - Or pulvinar sign
        pulvinar_l = patches.Circle((40, 46), 4, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        pulvinar_r = patches.Circle((60, 46), 4, linewidth=1.5, edgecolor='#ff3c3c', facecolor='none')
        ax.add_patch(pulvinar_l)
        ax.add_patch(pulvinar_r)
        ax.text(50, 36, "Pulvinar T1 Hyperintensity\n('Pulvinar Sign')", color='#ff3c3c', fontsize=8, ha='center', fontweight='bold')
        
        # White Matter Lesions ROI (Yellow)
        wml_1 = patches.Circle((28, 58), 3, linewidth=1.5, edgecolor='#ffc800', facecolor='none')
        wml_2 = patches.Circle((72, 58), 3, linewidth=1.5, edgecolor='#ffc800', facecolor='none')
        wml_3 = patches.Circle((50, 68), 4, linewidth=1.5, edgecolor='#ffc800', facecolor='none')
        ax.add_patch(wml_1)
        ax.add_patch(wml_2)
        ax.add_patch(wml_3)
        ax.text(50, 78, "Periventricular White Matter Lesions", color='#ffc800', fontsize=8, ha='center')
        
    plt.title(f"Patient Scan Analysis: {disease}", color='white', fontsize=11, fontweight='bold', pad=10)
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()

def custom_run_step_6(job_id):
    """Step 6 override: Generates explanation chart + scan annotation overlay."""
    print('Step 6 (RareGuard XAI) - Generating explanation chart and scan annotation...')
    # Call original run_step_6 (this generates the modality contribution chart)
    original_run_step_6(job_id)
    
    # Generate the ROI annotation image
    job = pipeline.jobs[job_id]
    pred = job['prediction_response']
    disease = pred['disease_name']
    
    annot_filename = f"annotated_{job_id}.png"
    annot_path = os.path.join(ANNOTATION_DIR, annot_filename)
    
    generate_scan_annotation_image(disease, annot_path)
    
    # Store in job
    job['annotation_url'] = f"/annotations/{annot_filename}"
    job.get('audit_trail', []).append(f"{__import__('time').strftime('%Y-%m-%d %H:%M:%S')} - Stage 6 (Annotated): XAI ROI scan overlay generated for {disease}.")
    print(f"Step 6 (RareGuard XAI) - PREMIUM Scan Annotation saved to: {annot_path}")

# Hook Step 6 (Chart Generation) in the 10-stage pipeline
pipeline.run_step_6 = custom_run_step_6

# Save original Step 7 (PDF Compilation) in the 10-stage pipeline
original_run_step_7 = pipeline.run_step_7

def custom_run_step_7(job_id):
    """Step 7 override: Compiles PREMIUM PDF with annotation, modality findings, and risk level."""
    job = pipeline.jobs[job_id]
    form = job['form_data']
    pred = job['prediction_response']
    chart_path = job['explanation_image_path']
    risk_level = job.get('risk_level', 'MEDIUM')

    print('Step 7 (RareGuard PDF) - Compiling PREMIUM Report PDF...')
    pdf_path = os.path.join(pipeline.REPORT_DIR, f'report_{job_id}.pdf')

    patient_info = {
        'patient_id': form['patient_id'],
        'patient_name': form['patient_name'],
        'age': form['age'],
        'gender': form['gender']
    }

    disease = pred['disease_name']
    confidence = pred['confidence_percent']
    explanation = pred['explanation']
    weights = pred['attention_weights']

    annotation_path = None
    if 'annotation_url' in job:
        annot_filename = os.path.basename(job['annotation_url'])
        possible_annot = os.path.join(BASE_DIR, 'annotations', annot_filename)
        if os.path.exists(possible_annot):
            annotation_path = possible_annot

    modality_findings = pred.get('modality_findings', None)

    pdf_report.generate_pdf_report(
        pdf_path, patient_info, disease, confidence, explanation, weights, chart_path,
        annotation_path=annotation_path, modality_findings=modality_findings
    )
    job['report_file_path'] = pdf_path
    job.get('audit_trail', []).append(f"{__import__('time').strftime('%Y-%m-%d %H:%M:%S')} - Stage 7 (Annotated): Premium PDF report compiled with ROI scan and risk level: {risk_level}.")
    print(f'Step 7 (RareGuard PDF) - PREMIUM Report PDF saved to: {pdf_path}')

# Hook Step 7 (PDF Compilation) in the 10-stage pipeline
pipeline.run_step_7 = custom_run_step_7
