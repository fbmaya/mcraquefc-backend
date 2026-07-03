from datetime import date, datetime
from pydantic import BaseModel


class MatchStatIn(BaseModel):
    student_id: str
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: float | None = None
    played: bool = True
    notes: str | None = None


class MatchCreate(BaseModel):
    date: date
    opponent: str
    location: str | None = None
    home: bool = True
    score_us: int | None = None
    score_them: int | None = None
    category: str | None = None
    notes: str | None = None
    stats: list[MatchStatIn] = []


class MatchUpdate(BaseModel):
    opponent: str | None = None
    location: str | None = None
    home: bool | None = None
    score_us: int | None = None
    score_them: int | None = None
    category: str | None = None
    notes: str | None = None


class MatchStatOut(BaseModel):
    id: str
    student_id: str
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    rating: float | None
    played: bool
    notes: str | None

    model_config = {"from_attributes": True}


class MatchOut(BaseModel):
    id: str
    school_id: str
    date: date
    opponent: str
    location: str | None
    home: bool
    score_us: int | None
    score_them: int | None
    category: str | None
    notes: str | None
    stats: list[MatchStatOut]
    created_at: datetime

    model_config = {"from_attributes": True}
