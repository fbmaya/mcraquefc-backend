from datetime import date, datetime
from pydantic import BaseModel


class AttendanceRecordIn(BaseModel):
    student_id: str
    present: bool
    justified: bool = False
    notes: str | None = None


class AttendanceSessionCreate(BaseModel):
    class_id: str
    date: date
    notes: str | None = None
    records: list[AttendanceRecordIn]


class AttendanceRecordOut(BaseModel):
    id: str
    session_id: str
    student_id: str
    present: bool
    justified: bool
    notes: str | None

    model_config = {"from_attributes": True}


class AttendanceSessionOut(BaseModel):
    id: str
    class_id: str
    date: date
    notes: str | None
    records: list[AttendanceRecordOut]
    created_at: datetime

    model_config = {"from_attributes": True}
