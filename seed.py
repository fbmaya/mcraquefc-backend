"""
Bootstraps the database with demo data (idempotent — safe to run on every boot):
  - 1 platform_admin (Meu Craque FC internal)
  - 1 demo school with trial license
  - 1 manager + 1 coach
  - 1 parent, linked to a demo student
  - demo classes, students, evaluations, matches and attendance

Usage: python seed.py

Logins (todos com senha "mudar123"):
  admin@meucraquefc.com   platform_admin  (painel :3001)
  gestor@demo.com         manager         (painel :3000)
  professor@demo.com      coach           (painel :3000)
  pai@demo.com            parent          (portal :3000)
"""
import uuid
import datetime as dt
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, engine, Base
import app.models  # noqa: registers all tables

Base.metadata.create_all(bind=engine)

from app.models.school import School
from app.models.license import License, PlanType, LicenseStatus
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.class_ import Class, ClassEnrollment
from app.models.evaluation import Evaluation
from app.models.match import Match, MatchStat
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.parent_link import ParentStudentLink
from app.auth.jwt import hash_password

db = SessionLocal()
PW = hash_password("mudar123")


def get_or_create_user(email, name, role, school_id):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user, False
    user = User(id=str(uuid.uuid4()), school_id=school_id, name=name,
                email=email, hashed_password=PW, role=role)
    db.add(user)
    return user, True


# ── Platform admin ────────────────────────────────────────────
get_or_create_user("admin@meucraquefc.com", "Admin Plataforma", UserRole.platform_admin, None)

# ── Demo school ───────────────────────────────────────────────
school = db.query(School).first()
if not school:
    school = School(id=str(uuid.uuid4()), name="Meu Craque FC Demo", primary_color="#6366f1")
    db.add(school)
    db.flush()
    db.add(License(id=str(uuid.uuid4()), school_id=school.id, plan=PlanType.trial,
                   status=LicenseStatus.active, max_students=30, max_coaches=2))
    print(f"[school] {school.name}")

# ── Staff ─────────────────────────────────────────────────────
get_or_create_user("gestor@demo.com", "Gestor Demo", UserRole.manager, school.id)
coach, _ = get_or_create_user("professor@demo.com", "Professor Demo", UserRole.coach, school.id)

# ── Parent ────────────────────────────────────────────────────
parent, _ = get_or_create_user("pai@demo.com", "Responsável Demo", UserRole.parent, None)

db.commit()

# ── Demo dataset (idempotente via guardian_email do 1º aluno) ─
DEMO_MARKER_EMAIL = "pai@demo.com"
if db.query(Student).filter(Student.guardian_email == DEMO_MARKER_EMAIL).first():
    print("[demo] dados de exemplo já existem")
    db.close()
    print("Done.")
    raise SystemExit(0)

print("[demo] criando turmas, alunos, avaliações, jogos e presenças...")

# Classes
turma_sub9 = Class(id=str(uuid.uuid4()), school_id=school.id, name="Sub-9 A",
                   age_group="Sub-9", schedule="Ter/Qui 18h", coach_id=coach.id)
turma_sub11 = Class(id=str(uuid.uuid4()), school_id=school.id, name="Sub-11 A",
                    age_group="Sub-11", schedule="Seg/Qua 19h", coach_id=coach.id)
db.add_all([turma_sub9, turma_sub11])

# Students. O 1º leva o guardian_email do pai demo — o vínculo é reconciliado
# no login por esse email (mesmo fluxo de produção).
students_spec = [
    ("Lucas Gabriel", "Ponta", "Esquerdo", "Ana Martins", turma_sub9, DEMO_MARKER_EMAIL),
    ("João Miguel", "Atacante", "Direito", "Carla Souza", turma_sub9, None),
    ("Pedro Henrique", "Meia", "Direito", "Marcos Alves", turma_sub11, None),
    ("Rafael Costa", "Zagueiro", "Direito", "Fernanda Costa", turma_sub11, None),
    ("Bruno Dias", "Goleiro", "Direito", "Paulo Dias", turma_sub9, None),
]
students = []
for name, pos, foot, guardian, turma, guardian_email in students_spec:
    s = Student(id=str(uuid.uuid4()), school_id=school.id, name=name, position=pos,
                foot=foot, guardian_name=guardian, guardian_email=guardian_email,
                guardian_phone="(11) 90000-0000", birth_date=dt.date(2016, 3, 12))
    db.add(s)
    db.add(ClassEnrollment(id=str(uuid.uuid4()), class_id=turma.id, student_id=s.id, active=True))
    students.append(s)

db.flush()

# Vincula o pai ao 1º aluno (o login também reconciliaria via guardian_email).
db.add(ParentStudentLink(id=str(uuid.uuid4()), parent_id=parent.id, student_id=students[0].id))


def evaluation(student, date, base):
    return Evaluation(
        id=str(uuid.uuid4()), student_id=student.id, evaluated_by=coach.id, date=date,
        passing=base, finishing=base - 0.5, dribbling=base + 1, speed=base, stamina=base - 0.5,
        agility=base, positioning=base - 1, decision=base - 0.5, discipline=base + 1,
        teamwork=base, attitude=base, commitment=base - 0.5, leadership=base - 1,
    )


# Lucas: duas avaliações (mostra evolução); demais: uma
db.add(evaluation(students[0], dt.date(2026, 5, 1), 6.0))
db.add(evaluation(students[0], dt.date(2026, 6, 1), 8.0))
for s, base in zip(students[1:], [7.0, 6.5, 7.5, 6.0]):
    db.add(evaluation(s, dt.date(2026, 6, 1), base))

# Match + estatísticas (alimenta a artilharia)
match = Match(id=str(uuid.uuid4()), school_id=school.id, date=dt.date(2026, 6, 10),
              opponent="Rival FC", location="Arena Norte", home=True,
              score_us=4, score_them=1, category="Sub-9")
db.add(match)
db.flush()
scorers = [(students[0], 2, 1), (students[1], 1, 0), (students[4], 0, 0)]
for s, goals, assists in scorers:
    db.add(MatchStat(id=str(uuid.uuid4()), match_id=match.id, student_id=s.id,
                     goals=goals, assists=assists, yellow_cards=0, red_cards=0,
                     rating=7.5 + goals * 0.5, played=True))

# Attendance (duas sessões da turma Sub-9)
for i, date in enumerate([dt.date(2026, 6, 3), dt.date(2026, 6, 5)]):
    session = AttendanceSession(id=str(uuid.uuid4()), class_id=turma_sub9.id, date=date)
    db.add(session)
    db.flush()
    for s in [students[0], students[1], students[4]]:
        present = not (i == 1 and s is students[1])  # João falta na 2ª
        db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=session.id,
                                student_id=s.id, present=present))

db.commit()
print(f"[demo] {len(students)} alunos, 2 turmas, avaliações, 1 jogo e 2 presenças criados")
db.close()
print("Done.")
