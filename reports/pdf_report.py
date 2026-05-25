import os
import sys
import json
import sqlite3
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import logger

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def generate_pdf_report(batch_id: str, db_path="data/durian.db", output_dir="reports/outputs"):
    logger.info(f"Generating PDF report for batch: {batch_id}")
    
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab is not installed or available on this platform. Cannot generate PDF.")
        return None

    # Create output directory
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"batch_report_{batch_id}.pdf"

    if not os.path.exists(db_path):
        logger.error(f"Database {db_path} not found. Cannot generate report.")
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Fetch batch
        cursor.execute("SELECT * FROM batches WHERE batch_id = ?;", (batch_id,))
        batch_row = cursor.fetchone()
        if not batch_row:
            logger.error(f"Batch {batch_id} not found in DB.")
            return None
        batch = dict(batch_row)

        # Fetch detections
        cursor.execute("SELECT * FROM detections WHERE batch_id = ?;", (batch_id,))
        detections = [dict(r) for r in cursor.fetchall()]

        # Setup PDF Document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Custom styles with explicit parents and leading (essential in ReportLab when changing fontSize)
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=15
        )
        
        h2_style = ParagraphStyle(
            name='H2Style',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=17,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=15,
            spaceAfter=8
        )
        
        body_style = ParagraphStyle(
            name='BodyStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6
        )

        bold_body = ParagraphStyle(
            name='BoldBody',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#2C3E50')
        )
        
        white_bold = ParagraphStyle(
            name='WhiteBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=colors.white
        )

        story = []

        # Document Header
        story.append(Paragraph(f"DURIAN CLASSIFIER REPORT", title_style))
        story.append(Paragraph(f"Batch Session Report for ID: {batch_id}", body_style))
        story.append(Spacer(1, 15))

        # Metadata Table
        metadata_data = [
            [Paragraph("Session Details", bold_body), ""],
            [Paragraph("Batch ID:", body_style), Paragraph(str(batch_id), body_style)],
            [Paragraph("Start Time:", body_style), Paragraph(str(batch.get("start_time") or "N/A"), body_style)],
            [Paragraph("End Time:", body_style), Paragraph(str(batch.get("end_time") or "Running"), body_style)],
            [Paragraph("Total Fruits Processed:", body_style), Paragraph(str(batch.get("total_count") if batch.get("total_count") is not None else 0), body_style)]
        ]
        
        meta_table = Table(metadata_data, colWidths=[150, 350])
        meta_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#2C3E50')),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))

        # Grade Distribution Section
        story.append(Paragraph("Grade Distribution Summary", h2_style))
        
        total = max(1, batch.get("total_count", 0))
        grade_data = [
            [Paragraph("Grade", white_bold), Paragraph("Count", white_bold), Paragraph("Percentage", white_bold)],
            [Paragraph("Grade A", body_style), Paragraph(str(batch.get("grade_a", 0)), body_style), Paragraph(f"{batch.get('grade_a', 0)/total*100:.1f}%", body_style)],
            [Paragraph("Grade B", body_style), Paragraph(str(batch.get("grade_b", 0)), body_style), Paragraph(f"{batch.get('grade_b', 0)/total*100:.1f}%", body_style)],
            [Paragraph("Grade C", body_style), Paragraph(str(batch.get("grade_c", 0)), body_style), Paragraph(f"{batch.get('grade_c', 0)/total*100:.1f}%", body_style)],
            [Paragraph("Reject", body_style), Paragraph(str(batch.get("reject", 0)), body_style), Paragraph(f"{batch.get('reject', 0)/total*100:.1f}%", body_style)],
        ]
        
        grade_table = Table(grade_data, colWidths=[200, 150, 150])
        grade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        story.append(grade_table)
        story.append(Spacer(1, 20))

        # Defect Frequency Section
        story.append(Paragraph("Defect Breakdown Statistics", h2_style))
        
        defect_counts = {'crack': 0, 'dark_spot': 0, 'fungus': 0, 'thorn_split': 0, 'reject': 0}
        for det in detections:
            try:
                labels = json.loads(det["defect_types"]) if det["defect_types"] else []
                for label in labels:
                    if label in defect_counts:
                        defect_counts[label] += 1
            except Exception:
                pass

        defect_data = [
            [Paragraph("Defect Category", white_bold), Paragraph("Frequency", white_bold)]
        ]
        for key, count in defect_counts.items():
            defect_data.append([Paragraph(key, body_style), Paragraph(str(count), body_style)])

        defect_table = Table(defect_data, colWidths=[250, 250])
        defect_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        story.append(defect_table)
        
        # Build Document
        doc.build(story)
        logger.info(f"PDF report successfully saved to: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Error compiling PDF report: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_pdf_report(sys.argv[1])
    else:
        print("Usage: python pdf_report.py <batch_id>")
