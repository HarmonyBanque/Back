from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models import User, Beneficiary, Account
from schemas import CreateBeneficiary, CreateAccount, CreateDeposit, IncomeResponse
from database import get_session
from typing import List, Optional
from route.auth import get_user

router = APIRouter()

@router.post("/", response_model=Beneficiary, tags=['Beneficiary'])
def create_beneficiary(body: CreateBeneficiary, user: User = Depends(get_user), session: Session = Depends(get_session)) -> Beneficiary:
    
    benefAccount = session.exec(select(Account).where(Account.account_number == body.beneficiary_account_number)).first()
    
    if benefAccount is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Beneficiary account not found")   
    
    benef = session.exec(select(Beneficiary).where(Beneficiary.beneficiary_account_number == body.beneficiary_account_number)).first()
    
    if benef is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Beneficiary already registered")
    
    beneficiary = Beneficiary(
        name=body.name,  
        account_number=body.account_number,
        beneficiary_account_number=body.beneficiary_account_number
    )
    session.add(beneficiary)
    session.commit()
    session.refresh(beneficiary)
    return beneficiary

@router.get("/{account_number}", response_model=List[Beneficiary], tags=['Beneficiary'])
def read_beneficiaries(account_number = str, session: Session = Depends(get_session)):
    beneficiaries = session.exec(select(Beneficiary).where(Beneficiary.account_number == account_number)).all()
    return beneficiaries
