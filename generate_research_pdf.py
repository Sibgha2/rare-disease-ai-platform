"""
generate_research_pdf.py — Converts research_paper_foundation.md to a premium IEEE-grade PDF
Uses ReportLab (already installed) to produce Research_Paper_Foundation.pdf
"""
import os
import re
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable

# ─── Brand Colors ───
C_BG       = colors.HexColor('#050a18')
C_INDIGO   = colors.HexColor('#4f46e5')
C_INDIGO_L = colors.HexColor('#818cf8')
C_TEAL     = colors.HexColor('#14b8a6')
C_TEAL_L   = colors.HexColor('#2dd4bf')
C_GOLD     = colors.HexColor('#f59e0b')
C_TEXT_0   = colors.HexColor('#0f172a')
C_TEXT_1   = colors.HexColor('#1e293b')
C_TEXT_2   = colors.HexColor('#475569')
C_TEXT_3   = colors.HexColor('#94a3b8')
C_BG_CARD  = colors.HexColor('#f1f5fb')
C_BG_CARD2 = colors.HexColor('#eef2ff')
C_BORDER   = colors.HexColor('#e2e8f0')

PAGE_W, PAGE_H = letter


class HeaderFooter:
    def __call__(self, canv, doc):
        canv.saveState()
        w, h = letter
        # Header
        canv.setFillColor(C_BG)
        canv.rect(0, h - 48, w, 48, fill=1, stroke=0)
        canv.setFillColor(C_INDIGO)
        canv.rect(0, h - 50, w * 0.6, 2, fill=1, stroke=0)
        canv.setFillColor(C_TEAL)
        canv.rect(w * 0.6, h - 50, w * 0.4, 2, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont('Helvetica-Bold', 11)
        canv.drawString(36, h - 30, 'RareGuard AI — Research Paper Foundation')
        canv.setFillColor(C_TEAL_L)
        canv.setFont('Helvetica', 7)
        canv.drawString(36, h - 40, 'Proactive Rare Disease Detection Platform')
        # Footer
        canv.setFillColor(colors.HexColor('#f1f5f9'))
        canv.rect(0, 0, w, 28, fill=1, stroke=0)
        canv.setFillColor(C_TEXT_2)
        canv.setFont('Helvetica', 7)
        canv.drawString(36, 10, f'Generated: {time.strftime("%d %B %Y")} — RareGuard AI Platform v3.0')
        canv.drawRightString(w - 36, 10, f'Page {doc.page}')
        canv.restoreState()


def make_styles():
    base = getSampleStyleSheet()
    def ps(name, **kw):
        return ParagraphStyle(name, parent=base['Normal'], **kw)
    return {
        'title': ps('t', fontName='Helvetica-Bold', fontSize=20, leading=26, textColor=C_TEXT_0, alignment=TA_CENTER, spaceAfter=6),
        'subtitle': ps('s', fontName='Helvetica', fontSize=10, leading=14, textColor=C_TEXT_2, alignment=TA_CENTER, spaceAfter=16),
        'h2': ps('h2', fontName='Helvetica-Bold', fontSize=14, leading=20, textColor=C_INDIGO, spaceBefore=18, spaceAfter=6),
        'h3': ps('h3', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=C_TEXT_0, spaceBefore=12, spaceAfter=4),
        'body': ps('b', fontName='Helvetica', fontSize=9.5, leading=14.5, textColor=C_TEXT_1, alignment=TA_JUSTIFY),
        'body_bold': ps('bb', fontName='Helvetica-Bold', fontSize=9.5, leading=14.5, textColor=C_TEXT_0),
        'bullet': ps('bu', fontName='Helvetica', fontSize=9.5, leading=14.5, textColor=C_TEXT_1, leftIndent=18, bulletIndent=6),
        'numbr': ps('nu', fontName='Helvetica', fontSize=9.5, leading=14.5, textColor=C_TEXT_1, leftIndent=18, bulletIndent=6),
        'table_head': ps('th', fontName='Helvetica-Bold', fontSize=8.5, leading=12, textColor=colors.white),
        'table_cell': ps('tc', fontName='Helvetica', fontSize=8.5, leading=12, textColor=C_TEXT_1),
        'table_cell_b': ps('tcb', fontName='Helvetica-Bold', fontSize=8.5, leading=12, textColor=C_TEXT_0),
    }


def parse_md_to_story(md_path, S):
    """Simple markdown-to-reportlab parser."""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    story = []
    W = PAGE_W - 72
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        # Build table
        header = table_rows[0]
        data_rows = table_rows[1:]  # skip separator row
        if len(data_rows) > 0 and all(c.strip().replace('-', '').replace('|', '') == '' for c in data_rows[0]):
            data_rows = data_rows[1:]

        col_count = len(header)
        col_w = W / col_count

        tdata = []
        # Header
        hcells = [Paragraph(c.strip().replace('**', ''), S['table_head']) for c in header]
        tdata.append(hcells)
        for row in data_rows:
            cells = []
            for i, c in enumerate(row):
                txt = c.strip().replace('**', '')
                style = S['table_cell_b'] if i == 0 else S['table_cell']
                cells.append(Paragraph(txt, style))
            tdata.append(cells)

        t = Table(tdata, colWidths=[col_w] * col_count)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), C_INDIGO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_BG_CARD, colors.white]),
            ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))
        table_rows = []
        in_table = False

    def clean_inline(text):
        """Convert **bold** and *italic* to reportlab tags."""
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = text.replace('`', '')
        return text

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line.strip():
            if in_table:
                flush_table()
            i += 1
            continue

        # Horizontal rules
        if line.strip() == '---':
            if in_table:
                flush_table()
            story.append(HRFlowable(width=W, color=C_INDIGO, thickness=1, spaceAfter=8, spaceBefore=8))
            i += 1
            continue

        # Table rows
        if '|' in line and line.strip().startswith('|'):
            cells = [c for c in line.split('|')[1:-1]]  # split and remove outer empties
            if all(c.strip().replace('-', '') == '' for c in cells):
                # separator row — skip
                i += 1
                continue
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            flush_table()

        # Headers
        if line.startswith('# '):
            story.append(Paragraph(clean_inline(line[2:].strip()), S['title']))
            i += 1
            continue
        if line.startswith('## '):
            story.append(Paragraph(clean_inline(line[3:].strip()), S['h2']))
            i += 1
            continue
        if line.startswith('### '):
            story.append(Paragraph(clean_inline(line[4:].strip()), S['h3']))
            i += 1
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.+)', line)
        if m:
            num = m.group(1)
            text = clean_inline(m.group(2))
            story.append(Paragraph(f'<b>{num}.</b> {text}', S['numbr']))
            i += 1
            continue

        # Bullet list
        if line.strip().startswith('* ') or line.strip().startswith('- '):
            text = clean_inline(line.strip()[2:])
            story.append(Paragraph(f'• {text}', S['bullet']))
            i += 1
            continue

        # Indented sub-bullet
        if line.strip().startswith('  - ') or line.strip().startswith('  * '):
            text = clean_inline(line.strip()[4:])
            bullet_style = ParagraphStyle('sub', parent=S['bullet'], leftIndent=36, bulletIndent=24)
            story.append(Paragraph(f'  ◦ {text}', bullet_style))
            i += 1
            continue

        # Regular paragraph
        text = clean_inline(line.strip())
        if text:
            story.append(Paragraph(text, S['body']))
            story.append(Spacer(1, 4))
        i += 1

    if in_table:
        flush_table()

    return story


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(BASE_DIR, 'research_paper_foundation.md')
    pdf_path = os.path.join(BASE_DIR, 'Research_Paper_Foundation.pdf')

    S = make_styles()
    hf = HeaderFooter()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=64, bottomMargin=42,
        title='RareGuard AI — Research Paper Foundation',
        author='RareGuard AI Platform',
        subject='Research Paper Foundation Document'
    )

    story = parse_md_to_story(md_path, S)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print(f'Research paper PDF generated: {pdf_path} ({os.path.getsize(pdf_path)} bytes)')


if __name__ == '__main__':
    main()
