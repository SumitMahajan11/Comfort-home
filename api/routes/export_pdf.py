"""
api/routes/export_pdf.py

Endpoint for generating a builder-ready construction specification PDF.
"""

from fastapi import APIRouter, Response, HTTPException

from api.loader import get_store
from api.models import PDFExportRequest
from api.pdf import build_builder_pdf

router = APIRouter(tags=["Export PDF"])

@router.post("/export/pdf")
def export_pdf(req: PDFExportRequest):
    """
    Generates and downloads a builder-ready passive design specification PDF.
    Contains BOM, 12-month temperature chart image, design variables, cost statement, and checksum footer.
    """
    store = get_store()
    pkg_data = req.package_data
    if not pkg_data:
        raise HTTPException(status_code=400, detail="Must provide 'package_data' in request body.")

    # Generate PDF buffer
    try:
        pdf_buf = build_builder_pdf(
            package_data=pkg_data,
            profile=req.profile,
            language=req.language or "en",
            project_title=req.project_title or "Passive Climate Design Specification",
            manifest_checksum=store.manifest_checksum
        )
        pdf_bytes = pdf_buf.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"Passive_Specification_{pkg_data.get('city', 'India')}_{pkg_data.get('building_type', 'house')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Manifest-Checksum": store.manifest_checksum
        }
    )
