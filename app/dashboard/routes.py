from fastapi import APIRouter, Depends, Query
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from datetime import datetime, time, timedelta
from typing import Optional, List
from collections import defaultdict
from bson import ObjectId

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    
    # Default to today if no dates provided
    if not start_date:
        start_date = datetime.combine(datetime.utcnow().date(), time.min)
    if not end_date:
        end_date = datetime.combine(datetime.utcnow().date(), time.max)
    
    # Ensure end_date is at the end of the day if it's just a date
    if end_date.time() == time.min:
        end_date = datetime.combine(end_date.date(), time.max)

    query = {
        "clinic_id": current_user.clinic_id,
        "created_at": {"$gte": start_date, "$lte": end_date}
    }

    # 1. Total patients in range
    unique_patients = await db.visits.distinct("patient_id", query)
    total_patients = len(unique_patients)
    
    # New patients (those whose first_visit_date is in range)
    new_patients = await db.patients.count_documents({
        "clinic_id": current_user.clinic_id,
        "first_visit_date": {"$gte": start_date, "$lte": end_date}
    })

    # 2. Revenue and Visits Breakdown
    visits_cursor = db.visits.find(query)
    visits_in_range = await visits_cursor.to_list(length=None)
    
    total_visits = len(visits_in_range)
    total_revenue = 0
    cash_revenue = 0
    online_revenue = 0
    
    payment_breakdown = defaultdict(float)
    
    for v in visits_in_range:
        fees = v.get("fees", 0)
        total_revenue += fees
        
        method = v.get("payment_method", "Cash").lower()
        payment_breakdown[method] += fees
        
        if method == "cash":
            cash_revenue += fees
        else:
            online_revenue += fees

    # 3. Monthly Revenue Trend (Last 6 months)
    six_months_ago = datetime.utcnow().replace(day=1) - timedelta(days=150) # Roughly 6 months
    monthly_query = {
        "clinic_id": current_user.clinic_id,
        "created_at": {"$gte": six_months_ago}
    }
    
    monthly_visits = await db.visits.find(monthly_query).to_list(length=None)
    monthly_stats = defaultdict(float)
    
    for v in monthly_visits:
        month_key = v["created_at"].strftime("%Y-%m") # e.g. "2024-03"
        monthly_stats[month_key] += v.get("fees", 0)
    
    # Convert to sorted list for the chart
    monthly_revenue_list = [
        {"month": k, "revenue": v} 
        for k, v in sorted(monthly_stats.items())
    ]

    # 4. Weekly/Daily breakdown within the selected range (if range is small)
    daily_stats = defaultdict(float)
    for v in visits_in_range:
        day_key = v["created_at"].strftime("%Y-%m-%d")
        daily_stats[day_key] += v.get("fees", 0)
    
    daily_revenue_list = [
        {"day": k, "revenue": v}
        for k, v in sorted(daily_stats.items())
    ]

    # 5. Demographics (Age & Gender) for patients in range
    patient_ids = [ObjectId(p_id) for p_id in unique_patients if ObjectId.is_valid(p_id)]
    
    gender_distribution = {}
    age_groups = {
        "0-18": 0,
        "19-35": 0,
        "36-50": 0,
        "51-70": 0,
        "71+": 0
    }

    if patient_ids:
        patients_in_range = await db.patients.find({"_id": {"$in": patient_ids}}).to_list(length=None)
        
        for p in patients_in_range:
            # Gender
            g = p.get("gender", "Unknown").capitalize()
            gender_distribution[g] = gender_distribution.get(g, 0) + 1
            
            # Age
            age = p.get("age", 0)
            if age <= 18: age_groups["0-18"] += 1
            elif age <= 35: age_groups["19-35"] += 1
            elif age <= 50: age_groups["36-50"] += 1
            elif age <= 70: age_groups["51-70"] += 1
            else: age_groups["71+"] += 1

    return {
        "summary": {
            "total_patients": total_patients,
            "new_patients": new_patients,
            "total_revenue": total_revenue,
            "total_visits": total_visits,
            "cash_revenue": cash_revenue,
            "online_revenue": online_revenue,
        },
        "payment_breakdown": dict(payment_breakdown),
        "monthly_revenue": monthly_revenue_list,
        "daily_revenue": daily_revenue_list,
        "demographics": {
            "gender": gender_distribution,
            "age": [
                {"group": k, "count": v} for k, v in age_groups.items()
            ]
        },
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }
