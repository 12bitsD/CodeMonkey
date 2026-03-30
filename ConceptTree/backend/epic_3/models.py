from pydantic import BaseModel
from typing import Optional


class NoteCreate(BaseModel):
    planId: str
    nodeId: str
    content: str


class NoteUpdate(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: str
    planId: str
    nodeId: str
    content: str
    date: str
    createdAt: str


class NoteListResponse(BaseModel):
    success: bool
    data: list
