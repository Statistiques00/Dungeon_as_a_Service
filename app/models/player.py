from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=30)
    hashed_password: str
