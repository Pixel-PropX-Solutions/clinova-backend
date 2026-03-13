from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from datetime import datetime
from typing import Optional
import pandas as pd
import io

router = APIRouter(prefix="/export", tags=["Exports"])

@router.get("/patients")
async def export_patients(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    query = {"clinic_id": current_user.clinic_id}
    
    if start_date or end_date:
        date_query = {}
        if start_date: date_query["$gte"] = start_date
        if end_date: date_query["$lte"] = end_date
        query["first_visit_date"] = date_query

    patients_cursor = db.patients.find(query, {"_id": 0, "clinic_id": 0, "visits": 0})
    patients = await patients_cursor.to_list(length=None)
    
    df = pd.DataFrame(patients)
    
    # Format dates for Excel/CSV
    if not df.empty:
        for col in ['first_visit_date', 'last_visit_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M')

    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=patients_{datetime.now().strftime('%Y%m%d')}.csv"
        return response
    else:
        stream = io.BytesIO()
        df.to_excel(stream, index=False, engine='openpyxl')
        stream.seek(0)
        response = StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f"attachment; filename=patients_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return response

@router.get("/bills")
async def export_bills(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    # Note: In this project, bills are actually visits by context of revenue
    # But if there's a separate bills collection, we filter that
    query = {"clinic_id": current_user.clinic_id}
    
    if start_date or end_date:
        date_query = {}
        if start_date: date_query["$gte"] = start_date
        if end_date: date_query["$lte"] = end_date
        query["created_at"] = date_query

    bills_cursor = db.bills.find(query, {"_id": 0, "clinic_id": 0, "services": 0})
    bills = await bills_cursor.to_list(length=None)
    
    df = pd.DataFrame(bills)

    if not df.empty and 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=bills_{datetime.now().strftime('%Y%m%d')}.csv"
        return response
    else:
        stream = io.BytesIO()
        df.to_excel(stream, index=False, engine='openpyxl')
        stream.seek(0)
        response = StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f"attachment; filename=bills_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return response
