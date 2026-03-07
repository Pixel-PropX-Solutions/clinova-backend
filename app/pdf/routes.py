from fastapi import APIRouter, Depends, HTTPException, Response
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from app.pdf.pdf_generator import generate_pdf
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


@router.get("/generate/{visit_id}/{template_id}")
async def generate_pdf_endpoint(visit_id: str, template_id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()

    # 1. Fetch Visit
    visit = await db.visits.find_one({"_id": ObjectId(visit_id), "clinic_id": current_user.clinic_id})
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # 2. Fetch Patient
    patient = await db.patients.find_one({"_id": ObjectId(visit["patient_id"])})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 3. Fetch Clinic info
    clinic = None
    if current_user.clinic_id:
        clinic = await db.clinics.find_one({"_id": ObjectId(current_user.clinic_id)})

    # 4. Resolve template_id — support "default" to use clinic's default
    actual_template_id = template_id
    if template_id == "default":
        if clinic and clinic.get("default_template_id"):
            actual_template_id = clinic["default_template_id"]
        else:
            raise HTTPException(status_code=400, detail="No default template set. Go to Settings to select one.")

    # 5. Fetch Template (allow global or clinic-specific)
    template_doc = await db.templates.find_one({"_id": ObjectId(actual_template_id)})
    if not template_doc:
        raise HTTPException(status_code=400, detail="Template not found")

    # 6. Build variable map — supports ${var}, {{var}}, and {var} patterns
    visit_date = visit.get("visited_at") or visit.get("created_at") or datetime.utcnow()
    if isinstance(visit_date, str):
        visit_date = datetime.fromisoformat(visit_date)

    variables = {
        # Patient
        "name": str(patient.get("name", "")),
        "phone": str(patient.get("phone", "")),
        "mobile": str(patient.get("phone", "")),
        "age": str(patient.get("age", "")),
        "gender": str(patient.get("gender", "")),
        "sex": str(patient.get("gender", "")),
        "address": str(patient.get("address", "")),

        # Visit
        "fees": str(visit.get("fees", 0)),
        "dr_name": str(visit.get("dr_name", "")),
        "disease": str(visit.get("disease", "")),
        "diagnosis": str(visit.get("diagnosis", "")),
        "specialization": str(visit.get("specialization", "")),
        "speciality": str(visit.get("specialization", "")),
        "payment_method": str(visit.get("payment_method", "Cash")),
        "date": visit_date.strftime("%d-%m-%Y"),
        "time": visit_date.strftime("%I:%M %p"),
        "datetime": visit_date.strftime("%d-%m-%Y %I:%M %p"),
        "medicines": ", ".join(visit.get("medicines", [])),

        # Clinic
        "clinic_name": str(clinic.get("name", "")) if clinic else "",
        "clinic_phone": str(clinic.get("phone", "")) if clinic else "",
        "clinic_email": str(clinic.get("email", "")) if clinic else "",
        "clinic_logo": str(clinic.get("logo_url", "")) if clinic else "",
    }

    # 7. Single-pass replacement using regex + hashmap lookup
    import re
    html_content = template_doc["html_content"]

    def replace_var(match):
        key = match.group(1)
        return variables.get(key, match.group(0))  # Keep original if not found

    # Matches ${key} and {{key}} patterns in one pass
    html_content = re.sub(r'\$\{([^}]+)\}|\{\{([^}]+)\}\}', 
        lambda m: variables.get(m.group(1) or m.group(2), m.group(0)), 
        html_content
    )
    
    # 8. Generate PDF
    pdf_bytes = await generate_pdf(html_content)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=parchi_{visit_id}.pdf"}
    )

