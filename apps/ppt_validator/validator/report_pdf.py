"""FROZEN — Legacy PDF report generator."""


def generate_pdf_report(result, output_path: str) -> None:
    """Generate a simple PDF report from a ValidationResult."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(output_path, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 780, f"PPT Validation Report: {result.filename}")
        c.setFont("Helvetica", 12)
        c.drawString(50, 750, f"Score: {result.score}/100")
        y = 720
        for v in result.violations:
            c.drawString(50, y, f"[Slide {v.slide}] {v.rule}: {v.message}")
            y -= 20
        c.save()
    except ImportError:
        pass
