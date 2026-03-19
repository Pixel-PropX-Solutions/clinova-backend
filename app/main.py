from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.config import settings
from app.auth.routes import router as auth_router
from app.clinics.routes import router as clinics_router
from app.patients.routes import router as patients_router
from app.visits.routes import router as visits_router

from app.templates.routes import router as templates_router
from app.pdf.routes import router as pdf_router
from app.exports.routes import router as exports_router
from app.dashboard.routes import router as dashboard_router
from app.settings.routes import router as settings_router
from app.utils.logger import log

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up Clinova backend...")
    await connect_to_mongo()
    yield
    log.info("Shutting down...")
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=[
    #             "https://clinova-frontend.vercel.app",
    #             "http://localhost:3000",
    #             "https://localhost:3000",
    #             "http://192.168.152.123:3000",
    #             "https://192.168.152.123:3000"
    # ],
    allow_origins=["*"],  # for dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(clinics_router, prefix=settings.API_V1_STR)
app.include_router(patients_router, prefix=settings.API_V1_STR)
app.include_router(visits_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(pdf_router, prefix=settings.API_V1_STR)
app.include_router(exports_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(settings_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
