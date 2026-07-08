from dataclasses import dataclass


@dataclass(frozen=True)
class Enrollment:
    id: str
    class_id: str
    student_id: str
    active: bool
