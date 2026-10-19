from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30, pattern=r"^[\w.-]+$")
]


class PlayerCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"username": "frodon", "password": "anneau-unique"}]}
    )

    username: Username
    password: str = Field(min_length=6, max_length=128)


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
