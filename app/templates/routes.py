from fastapi import APIRouter, Depends, HTTPException, status
from app.templates.models import (
    TemplateCreate,
    TemplateUpdate,
    TemplateInDB,
    TemplateCreateAdmin,
    TemplateUpdateAdmin,
)
from app.auth.dependencies import get_current_clinic_user, get_current_admin
from app.auth.models import TokenData
from app.database import get_db
from bson import ObjectId
from datetime import datetime
import re

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("/", response_model=TemplateInDB, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate, current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    template_dict = template.model_dump()
    template_db = TemplateInDB(**template_dict, clinic_id=current_user.clinic_id)

    result = await db.templates.insert_one(
        template_db.model_dump(by_alias=True, exclude=["id"])
    )
    created = await db.templates.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@router.get("/")
async def list_templates(current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()

    clinic = None
    if current_user.clinic_id:
        clinic = await db.clinics.find_one({"_id": ObjectId(current_user.clinic_id)})

    now = datetime.utcnow()
    dummy_variables = {
        "name": "John Doe",
        "phone": "9876543210",
        "mobile": "9876543210",
        "age": "30",
        "gender": "Male",
        "sex": "Male",
        "address": "Sample Street, Sample City",
        "fees": str(clinic.get("default_doctor_fee", 0)) if clinic else "0",
        "dr_name": str(clinic.get("default_doctor_name", "")) if clinic else "",
        "disease": "Fever",
        "diagnosis": "General Checkup",
        "specialization": "General Medicine",
        "speciality": "General Medicine",
        "payment_method": "Cash",
        "date": now.strftime("%d-%m-%Y"),
        "time": now.strftime("%I:%M %p"),
        "datetime": now.strftime("%d-%m-%Y %I:%M %p"),
        "medicines": "Paracetamol, Vitamin C",
        "clinic_name": str(clinic.get("name", "")) if clinic else "",
        "clinic_phone": str(clinic.get("phone", "")) if clinic else "",
        "clinic_email": str(clinic.get("email", "")) if clinic else "",
        "clinic_logo": str(clinic.get("logo_url", "")) if clinic else "",
        "clinic_address": str(clinic.get("address", "")) if clinic else "",
    }

    items = await db.templates.find(
        {"$or": [{"clinic_id": current_user.clinic_id}, {"is_global": True}]}
    ).to_list(100)

    for i in items:
        i["_id"] = str(i["_id"])

        html_content = i.get("html_content") or ""
     

        i["html_content"] = re.sub(
            r"\$\{([^}]+)\}|\{\{([^}]+)\}\}|\{([^{}]+)\}",
            lambda m: dummy_variables.get(
                (m.group(1) or m.group(2) or m.group(3)).strip(), m.group(0)
            ),
            html_content,
        )

    return items


@router.patch("/{id}", response_model=TemplateInDB)
async def update_template(
    id: str,
    template_update: TemplateUpdate,
    current_user: TokenData = Depends(get_current_clinic_user),
):
    db = get_db()
    update_data = {
        k: v for k, v in template_update.model_dump().items() if v is not None
    }
    update_data["updated_at"] = datetime.utcnow()

    result = await db.templates.update_one(
        {"_id": ObjectId(id), "clinic_id": current_user.clinic_id},
        {"$set": update_data},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")

    updated = await db.templates.find_one({"_id": ObjectId(id)})
    updated["_id"] = str(updated["_id"])
    return updated


@router.delete("/{id}")
async def delete_template(
    id: str, current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    result = await db.templates.delete_one(
        {"_id": ObjectId(id), "clinic_id": current_user.clinic_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"detail": "Template deleted"}


# --- Admin Routes ---


@router.post("/admin", response_model=TemplateInDB, status_code=status.HTTP_201_CREATED)
async def admin_create_template(
    template: TemplateCreateAdmin, current_user: TokenData = Depends(get_current_admin)
):
    db = get_db()

    if not template.is_global and not template.clinic_id:
        raise HTTPException(
            status_code=400, detail="Clinic ID is required for non-global templates"
        )

    if template.clinic_id and not template.is_global:
        # Verify clinic exists
        clinic = await db.clinics.find_one({"_id": ObjectId(template.clinic_id)})
        if not clinic:
            raise HTTPException(status_code=404, detail="Clinic not found")

    template_dict = template.model_dump()
    if template.is_global:
        template_dict["clinic_id"] = None

    template_db = TemplateInDB(**template_dict)
    result = await db.templates.insert_one(
        template_db.model_dump(by_alias=True, exclude=["id"])
    )
    created = await db.templates.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@router.get("/admin")
async def admin_list_templates(current_user: TokenData = Depends(get_current_admin)):
    db = get_db()
    items = await db.templates.find().to_list(100)  # Wait, maybe more? Let's say 1000
    for i in items:
        i["_id"] = str(i["_id"])
    return items


@router.patch("/admin/{id}", response_model=TemplateInDB)
async def admin_update_template(
    id: str,
    template_update: TemplateUpdateAdmin,
    current_user: TokenData = Depends(get_current_admin),
):
    db = get_db()
    update_data = {
        k: v for k, v in template_update.model_dump().items() if v is not None
    }
    update_data["updated_at"] = datetime.utcnow()

    if update_data.get("clinic_id") and not update_data.get("is_global", False):
        clinic = await db.clinics.find_one({"_id": ObjectId(update_data["clinic_id"])})
        if not clinic:
            raise HTTPException(status_code=404, detail="Clinic not found")

    if update_data.get("is_global"):
        update_data["clinic_id"] = None

    result = await db.templates.update_one({"_id": ObjectId(id)}, {"$set": update_data})

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")

    updated = await db.templates.find_one({"_id": ObjectId(id)})
    updated["_id"] = str(updated["_id"])
    return updated


@router.delete("/admin/{id}")
async def admin_delete_template(
    id: str, current_user: TokenData = Depends(get_current_admin)
):
    db = get_db()
    result = await db.templates.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"detail": "Template deleted"}
