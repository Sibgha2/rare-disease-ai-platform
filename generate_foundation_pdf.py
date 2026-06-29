import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

def generate_pdf(markdown_file, output_pdf):
    doc = SimpleDocTemplate(output_pdf, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    
    Story = []
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            Story.append(Spacer(1, 12))
            continue
            
        if line.startswith('# '):
            text = line[2:]
            Story.append(Paragraph(f"<b><font size=16>{text}</font></b>", styles['Heading1']))
            Story.append(Spacer(1, 12))
        elif line.startswith('## '):
            text = line[3:]
            Story.append(Paragraph(f"<b><font size=14>{text}</font></b>", styles['Heading2']))
            Story.append(Spacer(1, 12))
        elif line.startswith('### '):
            text = line[4:]
            Story.append(Paragraph(f"<b><font size=12>{text}</font></b>", styles['Heading3']))
            Story.append(Spacer(1, 12))
        elif line.startswith('* ') or line.startswith('- '):
            text = line[2:]
            parts = text.split('**')
            formatted = ""
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    formatted += f"<b>{part}</b>"
                else:
                    formatted += part
            Story.append(Paragraph(f"• {formatted}", styles['Normal']))
        elif line[0].isdigit() and line[1:3] == '. ':
            text = line[3:]
            parts = text.split('**')
            formatted = ""
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    formatted += f"<b>{part}</b>"
                else:
                    formatted += part
            Story.append(Paragraph(f"{line[:2]} {formatted}", styles['Normal']))
        else:
            text = line
            parts = text.split('**')
            formatted = ""
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    formatted += f"<b>{part}</b>"
                else:
                    formatted += part
            Story.append(Paragraph(formatted, styles['Justify']))

    doc.build(Story)
    print(f"PDF generated successfully at {output_pdf}")

if __name__ == '__main__':
    md_file = 'research_paper_foundation.md'
    pdf_file = 'Research_Paper_Foundation.pdf'
    generate_pdf(md_file, pdf_file)
