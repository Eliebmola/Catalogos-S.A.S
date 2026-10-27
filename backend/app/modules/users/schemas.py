from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UserProfileRead(BaseModel):
    email: str | None
    full_name: str | None


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: Annotated[str, Field(min_length=2, max_length=120)]
