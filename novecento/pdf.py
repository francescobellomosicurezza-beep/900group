from io import BytesIO
from itertools import groupby
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

MARRONE = colors.HexColor("#4E2E22")
ORO = colors.HexColor("#C9A24A")
CREMA = colors.HexColor("#F2EEE9")
GRIGIO = colors.HexColor("#D9D2CA")


def _stili():
    base = getSampleStyleSheet()
    return {
        "titolo": ParagraphStyle(
            "titolo",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=MARRONE,
            spaceAfter=2,
        ),
        "sottotitolo": ParagraphStyle(
            "sottotitolo",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=ORO,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "categoria": ParagraphStyle(
            "categoria",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=MARRONE,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "normale": ParagraphStyle(
            "normale", parent=base["Normal"], fontName="Helvetica", fontSize=10
        ),
        "piede": ParagraphStyle(
            "piede",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        ),
    }


def genera_pdf_ordine(ordine):
    """Restituisce il PDF dell'ordine come bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Ordine {ordine.numero} - {ordine.sede.nome}",
        author="Gelateria Novecento",
    )
    stili = _stili()
    creato = timezone.localtime(ordine.creato_il)
    elementi = [
        Paragraph("GELATERIA NOVECENTO", stili["sottotitolo"]),
        Paragraph(f"Ordine n. {ordine.numero}", stili["titolo"]),
        Spacer(1, 4 * mm),
    ]

    intestazione = Table(
        [
            ["Punto vendita", ordine.sede.nome],
            ["Operatore", ordine.operatore],
            ["Data e ora", f"{creato:%d/%m/%Y %H:%M}"],
            ["Articoli ordinati", str(ordine.righe.count())],
        ],
        colWidths=[45 * mm, None],
    )
    intestazione.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), MARRONE),
                ("BACKGROUND", (0, 0), (-1, -1), CREMA),
                ("BOX", (0, 0), (-1, -1), 0.5, GRIGIO),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elementi += [intestazione, Spacer(1, 6 * mm)]

    righe = list(ordine.righe.all())
    for categoria, gruppo in groupby(righe, key=lambda r: r.categoria_nome):
        dati = [["Articolo", "Quantità", "Unità"]]
        for riga in gruppo:
            dati.append(
                [Paragraph(escape(riga.articolo_nome), stili["normale"]), riga.quantita, riga.unita]
            )
        tabella = Table(dati, colWidths=[None, 25 * mm, 30 * mm], repeatRows=1)
        tabella.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), MARRONE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREMA]),
                    ("GRID", (0, 0), (-1, -1), 0.4, GRIGIO),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementi.append(
            KeepTogether([Paragraph(escape(categoria.upper()), stili["categoria"]), tabella])
        )

    if ordine.note:
        elementi += [
            Spacer(1, 6 * mm),
            Paragraph("NOTE", stili["categoria"]),
            Paragraph(escape(ordine.note).replace("\n", "<br/>"), stili["normale"]),
        ]

    elementi += [
        Spacer(1, 10 * mm),
        Paragraph(
            f"Documento generato automaticamente il {timezone.localtime():%d/%m/%Y %H:%M}",
            stili["piede"],
        ),
    ]
    doc.build(elementi)
    return buffer.getvalue()


def nome_file_pdf(ordine):
    creato = timezone.localtime(ordine.creato_il)
    return f"ordine_{ordine.sede.slug}_{creato:%Y%m%d}_{ordine.pk:05d}.pdf"
