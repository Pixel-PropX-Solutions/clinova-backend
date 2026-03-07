from fastapi import APIRouter, Depends, HTTPException, Response
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from app.pdf.pdf_generator import generate_pdf
from bson import ObjectId
from jinja2 import Template

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


@router.get("/generate/{visit_id}/{template_id}")
async def generate_pdf_endpoint(visit_id: str, template_id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    # 1. Fetch Visit
    visit = await db.visits.find_one({"_id": ObjectId(visit_id), "clinic_id": current_user.clinic_id})
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    patient = await db.patients.find_one({"_id": ObjectId(visit["patient_id"])})
    
    template_doc = await db.templates.find_one({
        "_id": ObjectId(template_id)
    })
    
    if not template_doc:
        raise HTTPException(status_code=400, detail="Template not found")
        
    # Inject Data
    
    html_content = template_doc["html_content"]
    
    variables = {
        "patient.name": patient.get("name", ""),
        "patient.phone": patient.get("phone", ""),
        "patient.age": str(patient.get("age", "")),
        "patient.gender": patient.get("gender", ""),
        "visit.disease": visit.get("disease", ""),
        "visit.diagnosis": visit.get("diagnosis", ""),
        "visit.dr_name": visit.get("dr_name", ""),
        "visit.fees": str(visit.get("fees", 0)),
        "visit.date": visit.get("visited_at", visit.get("created_at")).strftime("%d-%m-%Y")
    }
    
    # simple replacement loop for template variables like ${patient.name} or {{patient.name}}
    for key, value in variables.items():
        html_content = html_content.replace(f"${{{key}}}", value)
        html_content = html_content.replace(f"{{{{{key}}}}}", value)
        # Also handle user's specific format from example
        html_content = html_content.replace(f"${{OPDBills.name}}", variables["patient.name"])
        html_content = html_content.replace(f"${{OPDBills.age}}", variables["patient.age"])
        html_content = html_content.replace(f"${{OPDBills.sex}}", variables["patient.gender"])
        html_content = html_content.replace(f"${{OPDBills.mobile}}", variables["patient.phone"])
        html_content = html_content.replace(f"${{OPDBills.speciality}}", variables["visit.disease"])
        html_content = html_content.replace(f"${{OPDBills.Dr_Name}}", variables["visit.dr_name"])
        html_content = html_content.replace(f"${{OPDBills.address}}", "N/A")
        html_content = html_content.replace(f"${{OPDBills.fees}}", variables["visit.fees"])

    pdf_bytes = await generate_pdf(html_content, format_type="A4")
    
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=report_{visit_id}.pdf"}
    )
