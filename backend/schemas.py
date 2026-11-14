"""Request bodies for the API. Responses are plain dictionaries."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_CODE_CHARS = 200_000


class AnalyzeRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)
    language: Literal["auto", "js", "py"] = "auto"
    filename: Optional[str] = Field(default=None, max_length=120)

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Paste some code to analyze.")
        return v


class AddFileRequest(AnalyzeRequest):
    pass


class PredictRequest(BaseModel):
    text: str = Field(max_length=2000)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Describe the bug in a few words.")
        return v
