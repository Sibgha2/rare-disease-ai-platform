"""
pdf_report.py — Premium IEEE-Grade Patient-Friendly PDF Report Generator
for RareGuard AI: Proactive Rare Disease Detection Platform
"""
import os
import time
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, KeepTogether, HRFlowable, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas

# ─── Brand Colors ───────────────────────────────────────────────
C_BG         = colors.HexColor('#050a18')   # deep navy (header)
C_INDIGO     = colors.HexColor('#4f46e5')   # royal indigo
C_INDIGO_L   = colors.HexColor('#818cf8')   # light indigo
C_TEAL       = colors.HexColor('#14b8a6')   # emerald teal
C_TEAL_L     = colors.HexColor('#2dd4bf')   # light teal
C_GOLD       = colors.HexColor('#f59e0b')   # warm gold
C_SUCCESS    = colors.HexColor('#10b981')   # green
C_DANGER     = colors.HexColor('#f43f5e')   # red
C_WARN       = colors.HexColor('#f59e0b')   # amber

C_TEXT_0     = colors.HexColor('#0f172a')   # darkest text
C_TEXT_1     = colors.HexColor('#1e293b')   # body text
C_TEXT_2     = colors.HexColor('#475569')   # secondary
C_TEXT_3     = colors.HexColor('#94a3b8')   # muted

C_BG_PAGE    = colors.HexColor('#f8faff')   # page background
C_BG_CARD    = colors.HexColor('#f1f5fb')   # card background
C_BG_CARD2   = colors.HexColor('#eef2ff')   # indigo card
C_BORDER     = colors.HexColor('#e2e8f0')   # border

PAGE_W, PAGE_H = letter


# ═══════════════════════════════════════════════════════════════
# Custom Flowables
# ═══════════════════════════════════════════════════════════════

class ColoredRect(Flowable):
    """Draws a solid colored rectangle (for banners)."""
    def __init__(self, width, height, fill_color, radius=6):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)

    def wrap(self, availW, availH):
        return self.width, self.height


class SectionBanner(Flowable):
    """Draws a left-accented section header with icon and title."""
    def __init__(self, number, title, subtitle='', width=490, icon_char='▶'):
        super().__init__()
        self.number = number
        self.title = title
        self.subtitle = subtitle
        self.width = width
        self.height = 44
        self.icon_char = icon_char

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(C_BG_CARD2)
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        # Left accent bar
        c.setFillColor(C_INDIGO)
        c.roundRect(0, 0, 5, self.height, 3, fill=1, stroke=0)
        # Section number circle
        c.setFillColor(C_INDIGO)
        c.circle(22, self.height / 2, 10, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(22, self.height / 2 - 3.5, str(self.number))
        # Title
        c.setFillColor(C_TEXT_0)
        c.setFont('Helvetica-Bold', 12)
        c.drawString(40, self.height / 2 + 2, self.title.upper())
        # Subtitle
        if self.subtitle:
            c.setFillColor(C_TEXT_2)
            c.setFont('Helvetica-Oblique', 8)
            c.drawString(40, self.height / 2 - 9, self.subtitle)

    def wrap(self, availW, availH):
        return self.width, self.height


class ConfidenceBar(Flowable):
    """Visual confidence/progress bar."""
    def __init__(self, label, pct, color, width=440, bar_h=14):
        super().__init__()
        self.label = label
        self.pct = pct
        self.color = color
        self.width = width
        self.bar_h = bar_h
        self.height = bar_h + 22

    def draw(self):
        c = self.canv
        # Label
        c.setFillColor(C_TEXT_1)
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(0, self.bar_h + 8, self.label)
        # Pct
        c.setFont('Helvetica-Bold', 8)
        c.setFillColor(self.color)
        c.drawRightString(self.width, self.bar_h + 8, f"{self.pct:.1f}%")
        # Track
        c.setFillColor(colors.HexColor('#e2e8f0'))
        c.roundRect(0, 0, self.width, self.bar_h, 4, fill=1, stroke=0)
        # Fill
        fill_w = max(6, int(self.pct / 100 * self.width))
        c.setFillColor(self.color)
        c.roundRect(0, 0, fill_w, self.bar_h, 4, fill=1, stroke=0)

    def wrap(self, availW, availH):
        return self.width, self.height


class RiskGauge(Flowable):
    """Small risk level badge."""
    def __init__(self, level='HIGH', width=120, height=26):
        super().__init__()
        self.level = level.upper()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        colors_map = {
            'CRITICAL': (colors.HexColor('#fef2f2'), colors.HexColor('#dc2626')),
            'HIGH':     (colors.HexColor('#fff1f2'), colors.HexColor('#f43f5e')),
            'MEDIUM':   (colors.HexColor('#fffbeb'), colors.HexColor('#f59e0b')),
            'LOW':      (colors.HexColor('#f0fdf4'), colors.HexColor('#10b981')),
        }
        bg, fg = colors_map.get(self.level, colors_map['MEDIUM'])
        c.setFillColor(bg)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(fg)
        c.setFont('Helvetica-Bold', 9)
        label = f"● Risk: {self.level}"
        c.drawCentredString(self.width / 2, self.height / 2 - 3, label)

    def wrap(self, availW, availH):
        return self.width, self.height


class PageHeaderFooter:
    """Adds consistent header + footer to every page."""
    def __init__(self, patient_id, patient_name, report_date):
        self.patient_id = patient_id
        self.patient_name = patient_name
        self.report_date = report_date

    def __call__(self, canv, doc):
        canv.saveState()
        w, h = letter

        # ── Header ─────────────────────────────────────────────
        # Dark banner
        canv.setFillColor(C_BG)
        canv.rect(0, h - 56, w, 56, fill=1, stroke=0)
        # Gradient accent strip at bottom of header
        canv.setFillColor(C_INDIGO)
        canv.rect(0, h - 58, w * 0.6, 2, fill=1, stroke=0)
        canv.setFillColor(C_TEAL)
        canv.rect(w * 0.6, h - 58, w * 0.4, 2, fill=1, stroke=0)

        # Logo circle
        canv.setFillColor(C_INDIGO)
        canv.circle(36, h - 28, 16, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont('Helvetica-Bold', 10)
        canv.drawCentredString(36, h - 32, '⬡')

        # Title
        canv.setFillColor(colors.white)
        canv.setFont('Helvetica-Bold', 13)
        canv.drawString(58, h - 23, 'RareGuard AI')
        canv.setFillColor(C_TEAL_L)
        canv.setFont('Helvetica', 8)
        canv.drawString(58, h - 36, 'Proactive Rare Disease Detection Platform')

        # Patient pill (right side)
        canv.setFillColor(colors.HexColor('#0c1430'))
        canv.roundRect(w - 220, h - 46, 208, 28, 6, fill=1, stroke=0)
        canv.setFillColor(C_INDIGO_L)
        canv.setFont('Helvetica-Bold', 8)
        canv.drawString(w - 212, h - 28, f'Patient: {self.patient_name}')
        canv.setFillColor(C_TEXT_3)
        canv.setFont('Helvetica', 7)
        canv.drawString(w - 212, h - 39, f'ID: {self.patient_id} · {self.report_date}')

        # ── Footer ─────────────────────────────────────────────
        canv.setFillColor(colors.HexColor('#f1f5f9'))
        canv.rect(0, 0, w, 32, fill=1, stroke=0)
        canv.setFillColor(C_INDIGO)
        canv.rect(0, 32, w, 1, fill=1, stroke=0)
        canv.setFillColor(C_TEXT_2)
        canv.setFont('Helvetica-Oblique', 7.5)
        canv.drawString(36, 11, 'RAREGUARD AI — FOR CLINICAL DECISION SUPPORT ONLY — NOT A REPLACEMENT FOR PHYSICIAN JUDGMENT')
        canv.setFillColor(C_TEXT_2)
        canv.setFont('Helvetica', 7.5)
        canv.drawRightString(w - 36, 11, f'Page {doc.page}')

        canv.restoreState()


# ═══════════════════════════════════════════════════════════════
# Text Style Factory
# ═══════════════════════════════════════════════════════════════

def make_styles():
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base['Normal'], **kw)

    return {
        'title': ps('t_title',
            fontName='Helvetica-Bold', fontSize=24, leading=30,
            textColor=C_TEXT_0, alignment=TA_CENTER, spaceAfter=4),

        'subtitle': ps('t_sub',
            fontName='Helvetica', fontSize=11, leading=14,
            textColor=C_TEXT_2, alignment=TA_CENTER, spaceAfter=18),

        'disease': ps('t_disease',
            fontName='Helvetica-Bold', fontSize=18, leading=22,
            textColor=C_INDIGO, alignment=TA_CENTER),

        'confidence_val': ps('t_conf',
            fontName='Helvetica-Bold', fontSize=28, leading=34,
            textColor=C_SUCCESS, alignment=TA_CENTER),

        'body': ps('t_body',
            fontName='Helvetica', fontSize=10, leading=15,
            textColor=C_TEXT_1),

        'body_bold': ps('t_body_bold',
            fontName='Helvetica-Bold', fontSize=10, leading=15,
            textColor=C_TEXT_0),

        'body_sm': ps('t_body_sm',
            fontName='Helvetica', fontSize=9, leading=13,
            textColor=C_TEXT_1),

        'caption': ps('t_cap',
            fontName='Helvetica-Oblique', fontSize=8, leading=11,
            textColor=C_TEXT_3, alignment=TA_CENTER),

        'field_label': ps('t_fl',
            fontName='Helvetica-Bold', fontSize=8, leading=11,
            textColor=C_TEXT_3),

        'field_value': ps('t_fv',
            fontName='Helvetica-Bold', fontSize=10, leading=13,
            textColor=C_TEXT_0),

        'finding_head': ps('t_fh',
            fontName='Helvetica-Bold', fontSize=9, leading=12,
            textColor=C_INDIGO),

        'finding_body': ps('t_fb',
            fontName='Helvetica', fontSize=9, leading=13,
            textColor=C_TEXT_1),

        'disclaimer': ps('t_disc',
            fontName='Helvetica-Oblique', fontSize=8, leading=11.5,
            textColor=C_TEXT_2, alignment=TA_CENTER),

        'step_item': ps('t_step',
            fontName='Helvetica', fontSize=10, leading=15,
            textColor=C_TEXT_1, leftIndent=12),

        'step_bold': ps('t_stepb',
            fontName='Helvetica-Bold', fontSize=10, leading=15,
            textColor=C_TEXT_0, leftIndent=12),

        'highlight': ps('t_hl',
            fontName='Helvetica-Bold', fontSize=10, leading=15,
            textColor=C_INDIGO),
    }


# ═══════════════════════════════════════════════════════════════
# MAIN PDF GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_pdf_report(pdf_path, patient_info, diagnosis, confidence, explanation_txt, contributions, chart_path,
                        annotation_path=None, modality_findings=None, risk_level=None, trigger_type=None):

    report_date = time.strftime("%d %B %Y, %H:%M UTC")
    page_header_footer = PageHeaderFooter(
        patient_info.get('patient_id', '—'),
        patient_info.get('patient_name', '—'),
        time.strftime("%d %b %Y")
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=72, bottomMargin=48,
        title=f"RareGuard AI Diagnostic Report — {patient_info.get('patient_name', '')}",
        author="RareGuard AI Platform",
        subject="Proactive Rare Disease Detection — Clinical Diagnostic Report"
    )

    S = make_styles()
    story = []
    W = PAGE_W - 72  # usable width

    def spacer(n=8): return Spacer(1, n)
    def hr(color=C_BORDER, width=W): return HRFlowable(width=width, color=color, thickness=0.8, spaceAfter=6, spaceBefore=6)

    # ── TITLE BLOCK ─────────────────────────────────────────────
    story.append(spacer(8))
    story.append(Paragraph("CLINICAL DIAGNOSTIC REPORT", S['title']))
    story.append(Paragraph("RareGuard AI — Proactive Early Detection & Clinical Decision Support", S['subtitle']))
    story.append(hr(C_INDIGO, W * 0.6))
    story.append(spacer(12))

    # ── PATIENT INFO CARD ────────────────────────────────────────
    story.append(SectionBanner(1, "Patient Profile", "Demographics & report metadata", W))
    story.append(spacer(10))

    def info_cell(label, value):
        return [Paragraph(label, S['field_label']), Paragraph(str(value), S['field_value'])]

    patient_table_data = [
        info_cell("PATIENT ID", patient_info.get('patient_id', '—')),
        info_cell("FULL NAME", patient_info.get('patient_name', '—')),
        info_cell("AGE", f"{patient_info.get('age', '—')} years"),
        info_cell("BIOLOGICAL SEX", patient_info.get('gender', '—')),
        info_cell("REPORT DATE", report_date),
        info_cell("REPORT TYPE", "AI Multimodal Diagnostic Analysis"),
    ]

    # Arrange in 3 columns of 2 rows
    row1 = patient_table_data[0] + [Spacer(10,1)] + patient_table_data[1] + [Spacer(10,1)] + patient_table_data[2]
    row2 = patient_table_data[3] + [Spacer(10,1)] + patient_table_data[4] + [Spacer(10,1)] + patient_table_data[5]

    pt = Table(
        [row1, row2],
        colWidths=[60, 95, 10, 60, 100, 10, 60, 95],
        rowHeights=36
    )
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_CARD),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_BG_CARD, colors.white]),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('LINEAFTER', (1,0), (1,-1), 0.5, C_BORDER),
        ('LINEAFTER', (4,0), (4,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(KeepTogether([pt]))
    story.append(spacer(18))

    # ── DIAGNOSIS RESULT ─────────────────────────────────────────
    story.append(SectionBanner(2, "Predicted Diagnosis", "Primary AI classification result with confidence metrics", W))
    story.append(spacer(10))

    # Main diagnosis highlight box
    diag_inner = [
        [
            Paragraph('<font color="#94a3b8" size="8">PRIMARY DIAGNOSIS</font>', S['body']),
            Paragraph('<font color="#94a3b8" size="8">AI CONFIDENCE</font>', S['body']),
            Paragraph('<font color="#94a3b8" size="8">ANALYSIS TYPE</font>', S['body']),
        ],
        [
            Paragraph(f'<font color="#4f46e5"><b>{diagnosis}</b></font>', ParagraphStyle('dx', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=C_INDIGO)),
            Paragraph(f'<font color="#10b981"><b>{confidence:.1f}%</b></font>', ParagraphStyle('cf', fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=C_SUCCESS, alignment=TA_CENTER)),
            Paragraph('Multimodal Ensemble\nDeep Learning', ParagraphStyle('at', fontName='Helvetica', fontSize=9, leading=13, textColor=C_TEXT_2, alignment=TA_CENTER)),
        ]
    ]
    diag_table = Table(diag_inner, colWidths=[W * 0.48, W * 0.25, W * 0.27], rowHeights=[18, 44])
    diag_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_CARD2),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1.5, C_INDIGO),
        ('LINEAFTER', (0,0), (0,-1), 0.8, C_BORDER),
        ('LINEAFTER', (1,0), (1,-1), 0.8, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(KeepTogether([diag_table]))
    story.append(spacer(6))

    # Risk level badge (if provided)
    if risk_level:
        story.append(RiskGauge(level=risk_level, width=130, height=26))
        story.append(spacer(4))

    # Trigger type info (if surveillance)
    if trigger_type and trigger_type != 'direct_clinician':
        trigger_labels = {
            'death_registry': '🚨 SURVEILLANCE: Death Registry Family Screening Trigger',
            'hpo_surveillance': '🧠 SURVEILLANCE: HPO Minor Symptom Alert Trigger',
        }
        trigger_text = trigger_labels.get(trigger_type, f'Trigger: {trigger_type}')
        story.append(Paragraph(f'<font color="#f59e0b"><b>{trigger_text}</b></font>', S['body_bold']))
        story.append(spacer(4))

    story.append(spacer(6))

    # Confidence bars
    modality_labels = ['Imaging / MRI / CT Scan', 'Genetic Sequencing Data', 'Clinical Notes & History', 'Laboratory Panel Results']
    bar_colors = [C_INDIGO, C_TEAL, C_GOLD, C_SUCCESS]

    story.append(Paragraph("<b>Modality Contribution to Diagnosis:</b>", S['body_bold']))
    story.append(spacer(6))
    for i, (label, pct, col) in enumerate(zip(modality_labels, contributions, bar_colors)):
        story.append(ConfidenceBar(label, pct, col, width=W - 20))
        story.append(spacer(4))
    story.append(spacer(6))

    # Explanation box (plain language)
    story.append(Paragraph(
        '<b>What the AI Found — Plain Language Summary</b>',
        ParagraphStyle('expl_h', fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=C_GOLD)
    ))
    story.append(spacer(5))
    expl_table = Table(
        [[Paragraph(explanation_txt, S['body'])]],
        colWidths=[W]
    )
    expl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fffbeb')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fde68a')),
        ('LINEBEFORE', (0,0), (0,-1), 4, C_GOLD),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([expl_table]))
    story.append(spacer(18))

    # ── MODALITY CHART ───────────────────────────────────────────
    story.append(SectionBanner(3, "Data Analysis & Visualisations", "Modality weight chart and AI-annotated diagnostic scan", W))
    story.append(spacer(10))

    # Chart + Annotation side by side if both exist, else stacked
    chart_exists = chart_path and os.path.exists(chart_path)
    annot_exists = annotation_path and os.path.exists(annotation_path)

    if chart_exists and annot_exists:
        chart_cell = [
            Paragraph("<b>Modality Contribution Graph</b>", S['body_bold']),
            Spacer(1, 5),
            RLImage(chart_path, width=W * 0.48 - 8, height=int((W * 0.48 - 8) * 0.55)),
            Spacer(1, 4),
            Paragraph("Relative contribution of each data modality to the final AI prediction.", S['caption']),
        ]
        annot_cell = [
            Paragraph("<b>AI-Annotated Scan</b>", S['body_bold']),
            Spacer(1, 5),
            RLImage(annotation_path, width=W * 0.48 - 8, height=int((W * 0.48 - 8) * 0.67)),
            Spacer(1, 4),
            Paragraph("Coloured regions indicate AI-identified areas of clinical significance.", S['caption']),
        ]
        viz_table = Table(
            [[chart_cell, annot_cell]],
            colWidths=[W * 0.50, W * 0.50]
        )
        viz_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('BACKGROUND', (0,0), (-1,-1), C_BG_CARD),
            ('BOX', (0,0), (-1,-1), 1, C_BORDER),
            ('LINEAFTER', (0,0), (0,-1), 0.7, C_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(KeepTogether([viz_table]))

    elif chart_exists:
        story.append(Paragraph("<b>Modality Contribution Graph</b>", S['body_bold']))
        story.append(spacer(5))
        story.append(RLImage(chart_path, width=W * 0.7, height=int(W * 0.7 * 0.55)))
        story.append(Paragraph("Relative contribution of each data modality to the final AI prediction.", S['caption']))

    if annot_exists and not (chart_exists and annot_exists):
        story.append(spacer(10))
        story.append(Paragraph("<b>AI-Annotated Diagnostic Scan</b>", S['body_bold']))
        story.append(spacer(5))
        story.append(RLImage(annotation_path, width=W * 0.65, height=int(W * 0.65 * 0.67)))
        story.append(Paragraph("Coloured ROI regions indicate AI-identified areas of clinical significance.", S['caption']))

    story.append(spacer(18))

    # ── PER-MODALITY FINDINGS ─────────────────────────────────────
    if modality_findings:
        story.append(SectionBanner(4, "Modality-Specific Findings", "Detailed findings from each diagnostic data stream", W))
        story.append(spacer(10))

        finding_icons = {'imaging': '🧠', 'genetics': '🧬', 'clinical': '📋', 'labs': '🔬'}
        finding_colors = {'imaging': C_INDIGO, 'genetics': C_TEAL, 'clinical': colors.HexColor('#7c3aed'), 'labs': C_SUCCESS}

        cells = []
        for key, text in modality_findings.items():
            label = {'imaging': 'Imaging (MRI/CT)', 'genetics': 'Genetic Analysis', 'clinical': 'Clinical Notes', 'labs': 'Lab Results'}.get(key, key.title())
            col = finding_colors.get(key, C_INDIGO)
            cell = [
                Paragraph(f'<font color="{col.hexval()}"><b>■ {label}</b></font>', S['finding_head']),
                Spacer(1, 4),
                Paragraph(text, S['finding_body']),
            ]
            cells.append(cell)

        # 2-column grid
        rows = []
        for i in range(0, len(cells), 2):
            row = cells[i:i+2]
            if len(row) < 2:
                row.append([Spacer(1,1)])
            rows.append(row)

        findings_table = Table(rows, colWidths=[W / 2 - 6, W / 2 - 6])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_BG_CARD),
            ('BOX', (0,0), (-1,-1), 1, C_BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(KeepTogether([findings_table]))
        story.append(spacer(18))
        next_section = 5
    else:
        next_section = 4

    # ── NEXT STEPS ────────────────────────────────────────────────
    story.append(SectionBanner(next_section, "Recommended Clinical Actions", "Evidence-based next steps for this diagnosis", W))
    story.append(spacer(10))

    steps_general = [
        ("Specialist Consultation",
         "Refer to a clinical specialist experienced in rare diseases. The diagnosis should be reviewed by a board-certified physician before any treatment decisions.",
         C_INDIGO),
        ("Confirmatory Genetic Testing",
         "Order targeted genetic panel or whole-exome sequencing to confirm the identified pathogenic variant. Family cascade testing may also be indicated.",
         C_TEAL),
        ("Follow-Up Imaging",
         "Schedule follow-up MRI or CT scan in 3–6 months to monitor disease progression and assess treatment response.",
         C_GOLD),
        ("Patient & Family Counselling",
         "Engage a genetic counsellor to discuss disease inheritance, recurrence risk, and implications for biological relatives.",
         colors.HexColor('#7c3aed')),
        ("Multidisciplinary Team Review",
         "Present findings at an MDT meeting including neurology, genetics, radiology, and the primary care physician.",
         C_SUCCESS),
        ("Register with Rare Disease Registry",
         "Consider enrolling the patient in a relevant national/international rare disease registry to facilitate research and access to clinical trials.",
         colors.HexColor('#db2777')),
    ]

    steps_data = []
    for num, (title, desc, col) in enumerate(steps_general, 1):
        steps_data.append([
            Paragraph(f'<font color="{col.hexval()}"><b>{num}</b></font>',
                      ParagraphStyle('sn', fontName='Helvetica-Bold', fontSize=13, textColor=col, alignment=TA_CENTER)),
            Paragraph(f'<b>{title}</b><br/><font size="9" color="#475569">{desc}</font>',
                      ParagraphStyle('sc', fontName='Helvetica', fontSize=10, leading=14, textColor=C_TEXT_1)),
        ])

    steps_table = Table(steps_data, colWidths=[32, W - 32])
    steps_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_BG_CARD, colors.white]),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (0,-1), 8),
        ('RIGHTPADDING', (0,0), (0,-1), 4),
        ('LEFTPADDING', (1,0), (1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(KeepTogether([steps_table]))
    story.append(spacer(20))

    # ── DISCLAIMER ───────────────────────────────────────────────
    story.append(hr(C_INDIGO, W))
    story.append(spacer(6))
    disclaimer_text = (
        "<b>⚠ Medical Disclaimer:</b> This report has been generated by the RareGuard AI platform using calibrated ensemble deep-learning models trained on multimodal clinical data. "
        "It is intended as a <b>clinical decision support tool only</b> and does NOT constitute a final medical diagnosis. "
        "All findings must be reviewed, interpreted, and validated by a qualified healthcare professional before any clinical action is taken. "
        "The system does not replace physician judgment, clinical examination, or standard of care diagnostic procedures. "
        "Confidence scores are calibrated for missing-modality scenarios and represent model output probability, not clinical certainty. "
        "All data is processed in compliance with HIPAA and GDPR regulations."
    )
    disc_table = Table([[Paragraph(disclaimer_text, S['disclaimer'])]], colWidths=[W])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8faff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(disc_table)
    story.append(spacer(6))
    story.append(Paragraph(f"Report Reference: RGA-{patient_info.get('patient_id','X')}-{time.strftime('%Y%m%d%H%M')} · Generated by RareGuard AI Platform v3.0", S['caption']))

    # ── BUILD ─────────────────────────────────────────────────────
    doc.build(story, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
