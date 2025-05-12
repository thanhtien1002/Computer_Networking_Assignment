# backend/app/models.py
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    username: str
    password: str

class Message(BaseModel):
    user: str
    text: str
    timestamp: str

class Channel(BaseModel):
    id: str
    name: str