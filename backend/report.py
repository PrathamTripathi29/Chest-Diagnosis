from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import io
import base64
from datetime import datetime
import uuid

CONDITION_INFO = {
    'Pleural Effusion': {
        'description': (
            'Pleural effusion is the buildup of excess fluid between '
            'the layers of tissue that line the lungs and chest cavity. '
            'This fluid can compress the lung and make breathing difficult.'
        ),
        'urgency':      'HIGH',
        'urgency_text': 'Please consult a physician within 24 hours.',
        'symptoms': [
            'Shortness of breath',
            'Chest pain that worsens with breathing',
            'Dry cough',
            'Fever (if infection related)'
        ],
        'treatments': [
            'Thoracentesis (draining the fluid)',
            'Treating the underlying cause',
            'Diuretic medications',
            'Hospitalization if severe'
        ]
    },
    'Edema': {
        'description': (
            'Pulmonary edema is a condition in which excess fluid '
            'collects in the air sacs of the lungs, making it difficult '
            'to breathe. It is often caused by heart problems.'
        ),
        'urgency':      'HIGH',
        'urgency_text': 'Please consult a physician within 24 hours.',
        'symptoms': [
            'Difficulty breathing, especially when lying down',
            'Wheezing or gasping for breath',
            'Coughing up pink, foamy mucus',
            'Rapid or irregular heartbeat'
        ],
        'treatments': [
            'Supplemental oxygen',
            'Diuretic medications to reduce fluid',
            'Medications to strengthen heart function',
            'Treating underlying heart condition'
        ]
    },
    'Cardiomegaly': {
        'description': (
            'Cardiomegaly refers to an enlarged heart visible on imaging. '
            'It is not a disease itself but a sign of another condition '
            'such as heart disease, high blood pressure, or heart valve problems.'
        ),
        'urgency':      'MEDIUM',
        'urgency_text': 'Please consult a physician within 1 week.',
        'symptoms': [
            'Shortness of breath',
            'Abnormal heart rhythm',
            'Swelling in the legs',
            'Fatigue and dizziness'
        ],
        'treatments': [
            'Medications for heart failure',
            'Blood pressure management',
            'Lifestyle changes (diet, exercise)',
            'Surgery in severe cases'
        ]
    },
    'Pneumonia': {
        'description': (
            'Pneumonia is an infection that inflames the air sacs in one '
            'or both lungs, which may fill with fluid or pus.'
        ),
        'urgency':      'HIGH',
        'urgency_text': 'Please consult a physician within 24 hours.',
        'symptoms': [
            'Fever and chills',
            'Cough with phlegm',
            'Shortness of breath',
            'Chest pain when breathing'
        ],
        'treatments': [
            'Antibiotics (bacterial pneumonia)',
            'Antiviral medications (viral pneumonia)',
            'Rest and increased fluid intake',
            'Hospitalization if severe'
        ]
    },
    'No Finding': {
        'description': (
            'No significant abnormalities were detected in this chest X-ray. '
            'The lungs, heart, and visible structures appear within normal limits.'
        ),
        'urgency':      'LOW',
        'urgency_text': 'No immediate action required. Continue routine checkups.',
        'symptoms':     [],
        'treatments': [
            'Continue routine medical checkups',
            'Maintain a healthy lifestyle'
        ]
    }
}

COLORS = {
    'primary':    colors.HexColor('#1a73e8'),
    'high':       colors.HexColor('#d32f2f'),
    'medium':     colors.HexColor('#f57c00'),
    'low':        colors.HexColor('#388e3c'),
    'background': colors.HexColor('#f8f9fa'),
    'border':     colors.HexColor('#dee2e6'),
    'text':       colors.HexColor('#212529'),
    'subtext':    colors.HexColor('#6c757d'),
    'white':      colors.white
}


def get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', fontSize=24, fontName='Helvetica-Bold',
        textColor=COLORS['primary'], alignment=TA_CENTER, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader', fontSize=13, fontName='Helvetica-Bold',
        textColor=COLORS['primary'], spaceBefore=12, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='ConditionTitle', fontSize=12, fontName='Helvetica-Bold',
        textColor=COLORS['text'], spaceBefore=10, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name='GeneratedReportText', fontSize=10, fontName='Helvetica',
        textColor=COLORS['text'], leading=18, alignment=TA_JUSTIFY,
        leftIndent=12, rightIndent=12, spaceAfter=6,
        borderPad=10
    ))
    styles['BodyText'].fontSize  = 10
    styles['BodyText'].fontName  = 'Helvetica'
    styles['BodyText'].textColor = COLORS['text']
    styles['BodyText'].leading   = 16
    styles['BodyText'].alignment = TA_JUSTIFY
    styles['BodyText'].spaceAfter = 6
    styles.add(ParagraphStyle(
        name='BulletItem', fontSize=10, fontName='Helvetica',
        textColor=COLORS['text'], leftIndent=20, spaceAfter=3
    ))
    styles.add(ParagraphStyle(
        name='Disclaimer', fontSize=9, fontName='Helvetica-Oblique',
        textColor=COLORS['subtext'], alignment=TA_JUSTIFY, leading=14
    ))
    styles.add(ParagraphStyle(
        name='SmallNote', fontSize=9, fontName='Helvetica-Oblique',
        textColor=COLORS['subtext'], spaceAfter=8
    ))
    return styles


def urgency_color(urgency: str):
    return {
        'HIGH':   COLORS['high'],
        'MEDIUM': COLORS['medium'],
        'LOW':    COLORS['low']
    }.get(urgency, COLORS['subtext'])


def decode_heatmap_image(b64_string: str, width=3*inch, height=3*inch):
    return RLImage(
        io.BytesIO(base64.b64decode(b64_string)),
        width=width, height=height
    )


def confidence_bar_table(confidence: float, urgency: str, styles):
    bar_color = urgency_color(urgency)
    filled    = int(confidence / 5)
    bar_text  = '█' * filled + '░' * (20 - filled)
    data = [[
        Paragraph(
            f'<font color="#{bar_color.hexval()[2:]}"><b>{bar_text}</b></font>',
            styles['BodyText']
        ),
        Paragraph(f'<b>{confidence}%</b>', styles['BodyText'])
    ]]
    t = Table(data, colWidths=[4*inch, 1*inch])
    t.setStyle(TableStyle([
        ('ALIGN',  (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t


def build_report(predictions, heatmaps, scan_id=None, generated_report=None):
    if scan_id is None:
        scan_id = str(uuid.uuid4())[:8].upper()

    buffer   = io.BytesIO()
    styles   = get_styles()
    doc      = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2*cm,     bottomMargin=2*cm
    )
    elements = []

    # ── Header ────────────────────────────────────────────
    elements.append(Paragraph("ChestAI Analysis Report", styles['ReportTitle']))
    elements.append(Paragraph(
        f"Scan ID: <b>#{scan_id}</b> &nbsp;&nbsp; Date: <b>{datetime.now().strftime('%B %d, %Y')}</b>",
        ParagraphStyle('meta', parent=styles['BodyText'],
                       alignment=TA_CENTER, textColor=COLORS['subtext'])
    ))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=COLORS['border']))
    elements.append(Spacer(1, 0.2*inch))

    # ── AI Radiology Report ───────────────────────────────
    # This section comes FIRST — it's the most radiologist-like text
    # Generated by BLIP model trained on real MIMIC-CXR reports
    if generated_report:
        elements.append(Paragraph("AI Radiology Report", styles['SectionHeader']))
        elements.append(Paragraph(
            "Generated by a deep learning model trained on real radiologist "
            "reports from the MIMIC-CXR dataset (227,835 chest X-rays):",
            styles['SmallNote']
        ))
        # Light blue background box for the generated report
        report_data = [[
            Paragraph(generated_report, styles['GeneratedReportText'])
        ]]
        report_table = Table(report_data, colWidths=[6.5*inch])
        report_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EBF4FF')),
            ('ROUNDEDCORNERS', [8]),
            ('BOX',        (0,0), (-1,-1), 0.5, COLORS['primary']),
            ('PADDING',    (0,0), (-1,-1), 12),
        ]))
        elements.append(report_table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=COLORS['border']))
        elements.append(Spacer(1, 0.2*inch))

    # ── Findings Summary Table ────────────────────────────
    elements.append(Paragraph("AI Classification Results", styles['SectionHeader']))
    if not predictions:
        elements.append(Paragraph(
            "No significant findings detected. The chest X-ray appears within normal limits.",
            styles['BodyText']
        ))
    else:
        summary_data = [[
            Paragraph('<b>Condition</b>',  styles['BodyText']),
            Paragraph('<b>Confidence</b>', styles['BodyText']),
            Paragraph('<b>Urgency</b>',    styles['BodyText'])
        ]]
        for pred in predictions:
            info      = CONDITION_INFO.get(pred['condition'], {})
            urgency   = info.get('urgency', 'MEDIUM')
            urg_color = urgency_color(urgency)
            summary_data.append([
                Paragraph(pred['condition'], styles['BodyText']),
                Paragraph(f"<b>{pred['confidence']}%</b>", styles['BodyText']),
                Paragraph(
                    f'<font color="#{urg_color.hexval()[2:]}"><b>{urgency}</b></font>',
                    styles['BodyText']
                )
            ])
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND',     (0,0), (-1,0),  COLORS['primary']),
            ('TEXTCOLOR',      (0,0), (-1,0),  COLORS['white']),
            ('FONTNAME',       (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',       (0,0), (-1,-1), 10),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [COLORS['background'], COLORS['white']]),
            ('GRID',           (0,0), (-1,-1), 0.5, COLORS['border']),
            ('ALIGN',          (0,0), (-1,-1), 'LEFT'),
            ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING',        (0,0), (-1,-1), 8),
        ]))
        elements.append(summary_table)

    elements.append(Spacer(1, 0.3*inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=COLORS['border']))

    # ── Detailed Findings ─────────────────────────────────
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Detailed Findings", styles['SectionHeader']))

    for pred in predictions:
        condition = pred['condition']
        info      = CONDITION_INFO.get(condition, {})
        urgency   = info.get('urgency', 'MEDIUM')
        urg_color = urgency_color(urgency)

        elements.append(Paragraph(
            f'{condition} &nbsp; <font color="#{urg_color.hexval()[2:]}"><b>{urgency}</b></font>',
            styles['ConditionTitle']
        ))
        elements.append(confidence_bar_table(pred['confidence'], urgency, styles))
        elements.append(Spacer(1, 0.1*inch))

        if condition in heatmaps:
            elements.append(Paragraph(
                "Region of Interest (Grad-CAM Heatmap):", styles['BodyText']
            ))
            elements.append(decode_heatmap_image(heatmaps[condition]))
            elements.append(Paragraph(
                "<i>Red areas indicate regions the model focused on for this finding.</i>",
                ParagraphStyle('caption', parent=styles['BodyText'],
                               textColor=COLORS['subtext'], fontSize=9)
            ))
            elements.append(Spacer(1, 0.1*inch))

        elements.append(Paragraph("What is this?", styles['ConditionTitle']))
        elements.append(Paragraph(info.get('description', ''), styles['BodyText']))
        elements.append(Paragraph(
            f'<font color="#{urg_color.hexval()[2:]}"><b>Recommended Action:</b></font> '
            f'{info.get("urgency_text", "")}',
            styles['BodyText']
        ))

        if info.get('symptoms'):
            elements.append(Paragraph("Common Symptoms:", styles['ConditionTitle']))
            for symptom in info['symptoms']:
                elements.append(Paragraph(f"• {symptom}", styles['BulletItem']))

        if info.get('treatments'):
            elements.append(Paragraph("Standard Treatments:", styles['ConditionTitle']))
            for treatment in info['treatments']:
                elements.append(Paragraph(f"• {treatment}", styles['BulletItem']))

        elements.append(Spacer(1, 0.2*inch))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=COLORS['border']))

    # ── Disclaimer ────────────────────────────────────────
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Important Disclaimer", styles['SectionHeader']))
    elements.append(Paragraph(
        "This report has been generated by an AI-assisted image analysis system "
        "and is intended for informational and screening purposes only. "
        "It does not constitute a medical diagnosis and should not be used as a "
        "substitute for professional medical advice, diagnosis, or treatment. "
        "Always consult a qualified radiologist or physician before making any "
        "medical decisions. The AI model may produce false positives or false "
        "negatives. In case of emergency, contact your local emergency services immediately.",
        styles['Disclaimer']
    ))

    doc.build(elements)
    return buffer.getvalue(), scan_id