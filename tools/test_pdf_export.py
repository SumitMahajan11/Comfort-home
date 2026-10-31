"""
tools/test_pdf_export.py

Executes direct verification of the Builder-Ready PDF Export Engine (E-035).
Generates a PDF using the FastAPI /api/v1/export/pdf endpoint and prints literal byte count.
"""

from fastapi.testclient import TestClient
from api.main import app

def main():
    print("Executing Builder-Ready PDF Export Engine verification...")
    with TestClient(app) as client:
        pkg_resp = client.get('/api/v1/packages?city=Jodhpur&type=house&scenario=current')
        assert pkg_resp.status_code == 200, f"Failed to get package: {pkg_resp.text}"
        pkg_data = pkg_resp.json()['packages']['balanced']
        pkg_data['city'] = 'Jodhpur'
        pkg_data['building_type'] = 'house'

        payload = {
            'package_data': pkg_data,
            'language': 'en',
            'project_title': 'Passive Construction Specification'
        }
        resp = client.post('/api/v1/export/pdf', json=payload)
        assert resp.status_code == 200, f"Failed to export PDF: {resp.text}"
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-"), "Invalid PDF header"
        byte_size = len(resp.content)
        formatted_size = f"{byte_size:,}"
        print(f"PDF Export status: HTTP {resp.status_code}")
        print(f"Generated PDF bytes: {byte_size} ({formatted_size} bytes)")
        print(f"Checksum header: {resp.headers.get('x-manifest-checksum')}")
        print("Builder-Ready PDF Export Engine verified successfully.")

if __name__ == "__main__":
    main()
