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

    # Update patient aggregate fields only; visit records live in the visits collection.
    await db.patients.update_one(
        {"_id": ObjectId(visit.patient_id)},
        {
            "$inc": {"visit_count": 1},
            "$set": {"last_visit_date": created_visit.get("visited_at") or created_visit["created_at"]},
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

    # 3. Recompute patient aggregate fields from remaining visits.
    remaining_count = await db.visits.count_documents({
        "patient_id": patient_id,
        "clinic_id": current_user.clinic_id,
    })
    latest_visit = await db.visits.find_one(
        {
            "patient_id": patient_id,
            "clinic_id": current_user.clinic_id,
        },
        sort=[("visited_at", -1), ("created_at", -1)]
    )
    await db.patients.update_one(
        {"_id": ObjectId(patient_id)},
        {
            "$set": {
                "visit_count": remaining_count,
                "last_visit_date": (latest_visit.get("visited_at") or latest_visit.get("created_at")) if latest_visit else None,
            }
        }
    )

    return None
