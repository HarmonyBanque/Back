from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timedelta



class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    username: str = Field(index=True, unique=True)  

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: float
    creation_date: datetime = Field(default_factory=datetime.utcnow)
    account_number: str = Field(index=True, unique=True)
    isMain: bool = False
    isActive: bool = True
    name: str  
    type: str


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: str = Field(foreign_key="account.account_number")
    receiver_id: str = Field(foreign_key="account.account_number")
    amount: float
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    status: int
    description: Optional[str] = None  

class Deposit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_number: str = Field(foreign_key="account.account_number")
    amount: float
    deposit_date: datetime = Field(default_factory=datetime.utcnow)
    
class Automatique_transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_account: str = Field(foreign_key="account.account_number")
    receiver_account: str = Field(foreign_key="account.account_number")
    amount: float
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    occurence: int  # En secondes
    description: Optional[str] = None
    next_run: datetime = Field(default_factory=datetime.utcnow)

class Beneficiary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    account_number: str = Field(foreign_key="account.account_number")
    beneficiary_account_number: str = Field(foreign_key="account.account_number")

