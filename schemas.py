from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class CreateUser(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginUser(BaseModel):
    email: EmailStr
    password: str

class CreateAccount(BaseModel):
    name: str  
    type: str
    
class CreateTransaction(BaseModel):
    sender_id: str
    receiver_id: str
    amount: float
    description: Optional[str] = None  

class CreateDeposit(BaseModel):
    account_number: str
    amount: float

class UserResponse(BaseModel):
    email: EmailStr
    username: str  

class IncomeResponse(BaseModel):
    account_number: str
    amount: float
    date: datetime
    type: str
    description: Optional[str] = None  

    class Config:
        from_attributes = True
        
class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
class ChangeEmail(BaseModel):
    current_email: EmailStr
    new_email: EmailStr
    password: str 