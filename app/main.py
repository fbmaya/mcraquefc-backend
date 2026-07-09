from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.contexts.identity.interface import auth_router as auth
from app.contexts.performance.interface import matches_router as matches
from app.contexts.school.interface import classes_router as classes
from app.contexts.athletes.interface import students_router as students
from app.contexts.athletes.interface import parent_router as athletes_parent
from app.contexts.attendance.interface import attendance_router as attendance
from app.contexts.billing.interface import payments_router as payments
from app.contexts.assessment.interface import evaluations_router as evaluations
from app.contexts.reporting.interface import stats_router as stats
from app.contexts.platform.interface import platform_router as platform

app = FastAPI(title="Meu Craque FC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(athletes_parent.router)
app.include_router(classes.router)
app.include_router(payments.router)
app.include_router(evaluations.router)
app.include_router(matches.router)
app.include_router(attendance.router)
app.include_router(platform.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok"}
