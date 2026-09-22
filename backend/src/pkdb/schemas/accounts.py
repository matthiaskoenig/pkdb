from pydantic import BaseModel, ConfigDict, Field


class AccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(AccountInput):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=1024)


class Registration(Login):
    email: str = Field(
        min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )


class EmailRequest(AccountInput):
    email: str = Field(
        min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )


class Verification(AccountInput):
    key: str = Field(min_length=1, max_length=1024)


class PasswordReset(Verification):
    password: str = Field(min_length=8, max_length=1024)


class EmailCreate(EmailRequest):
    is_primary: bool = False


class EmailUpdate(AccountInput):
    email: str | None = Field(
        default=None,
        min_length=3,
        max_length=320,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    is_primary: bool = False
