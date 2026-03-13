from fastapi import APIRouter, Depends, HTTPException, status
from app.visits.models import VisitCreate, VisitInDB
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from bson import ObjectId

router = APIRouter(prefix="/visits", tags=["Visits"])

@router.post("/", response_model=VisitInDB, status_code=status.HTTP_201_CREATED)
async def create_visit(visit: VisitCreate, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    
    # Verify patient exists and belongs to clinic
    patient = await db.patients.find_one({
        "_id": ObjectId(visit.patient_id),
        "clinic_id": current_user.clinic_id
    })
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or does not belong to your clinic")
        
    visit_dict = visit.model_dump()
    visit_db = VisitInDB(**visit_dict, clinic_id=current_user.clinic_id)
    
    result = await db.visits.insert_one(visit_db.model_dump(by_alias=True, exclude=["id"]))
    created_visit = await db.visits.find_one({"_id": result.inserted_id})
    created_visit["_id"] = str(created_visit["_id"])
    
    # Update patient: increment visit count, set last visit date, push visit to embedded array
    visit_summary = {
        "visit_id": str(result.inserted_id),
        "fees": created_visit.get("fees", 0),
        "dr_name": created_visit.get("dr_name"),
        "disease": created_visit.get("disease"),
        "specialization": created_visit.get("specialization"),
        "payment_method": created_visit.get("payment_method", "Cash"),
        "visited_at": created_visit.get("visited_at"),
        "created_at": created_visit.get("created_at"),
    }
    
    await db.patients.update_one(
        {"_id": ObjectId(visit.patient_id)},
        {
            "$inc": {"visit_count": 1},
            "$set": {"last_visit_date": created_visit["created_at"]},
            "$push": {"visits": visit_summary}
        }
    )
    
    return created_visit

@router.get("/{patient_id}")
async def list_visits(patient_id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    # Verify patient ownership
    patient = await db.patients.find_one({
        "_id": ObjectId(patient_id),
        "clinic_id": current_user.clinic_id
    })
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    visits = await db.visits.find({
        "patient_id": patient_id, 
        "clinic_id": current_user.clinic_id
    }).sort("created_at", -1).to_list(100)
    
    for v in visits:
        v["_id"] = str(v["_id"])
        
    return visits

@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(visit_id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    
    # 1. Fetch visit to get patient_id
    visit = await db.visits.find_one({"_id": ObjectId(visit_id), "clinic_id": current_user.clinic_id})
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    patient_id = visit["patient_id"]
    
    # 2. Delete the visit
    await db.visits.delete_one({"_id": ObjectId(visit_id)})
    
    # 3. Update patient: decrement visit count, remove visit from array
    await db.patients.update_one(
        {"_id": ObjectId(patient_id)},
        {
            "$inc": {"visit_count": -1},
            "$pull": {"visits": {"visit_id": visit_id}}
        }
    )
    
    # 4. Update last_visit_date to the latest remaining visit
    updated_patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    if updated_patient and updated_patient.get("visits") and len(updated_patient["visits"]) > 0:
        # Sort visits to find the latest
        remaining_visits = updated_patient["visits"]
        latest_visit = max(remaining_visits, key=lambda x: x.get("visited_at") or x.get("created_at"))
        await db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": {"last_visit_date": latest_visit.get("visited_at") or latest_visit.get("created_at")}}
        )
    elif updated_patient:
        await db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": {"last_visit_date": None}}
        )

    return None
