from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, students, classes, payments, evaluations, matches, attendance, parent, platform, stats

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
app.include_router(classes.router)
app.include_router(payments.router)
app.include_router(evaluations.router)
app.include_router(matches.router)
app.include_router(attendance.router)
app.include_router(parent.router)
app.include_router(platform.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok"}
