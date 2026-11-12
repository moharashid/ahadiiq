from pydantic import BaseModel

class InvitationCreate(BaseModel):
    email: str
    role: str = "member"