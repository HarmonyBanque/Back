from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models import User, Account, Deposit, Transaction
from schemas import CreateUser, CreateAccount, CreateDeposit
from database import get_session
from typing import List, Optional
from route.auth import get_user

router = APIRouter()

@router.post("/", response_model=List[Deposit], tags=['deposit'])
def create_deposit(
    body: CreateDeposit, 
    user: User = Depends(get_user), 
    session: Session = Depends(get_session)
) -> List[Deposit]:
    # Vérifier si le compte cible existe et appartient à l'utilisateur
    account = session.exec(
        select(Account).where(
            Account.user_id == user.id, 
            Account.account_number == body.account_number, 
            Account.isActive == True
        )
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    deposits = [] 

    potential_balance = account.balance + body.amount

    if potential_balance > 50000:
        amount_to_fill = 50000 - account.balance

        account.balance = 50000
        session.add(account)
        deposit1 = Deposit(account_number=account.account_number, amount=amount_to_fill)
        session.add(deposit1)
        deposits.append(deposit1)

        main_account = session.exec(
            select(Account).where(
                Account.user_id == user.id, 
                Account.isMain == True
            )
        ).first()

        if main_account:
            excess_amount = potential_balance - 50000

            main_account.balance += excess_amount
            session.add(main_account)
            deposit2 = Deposit(account_number=main_account.account_number, amount=excess_amount)
            session.add(deposit2)
            deposits.append(deposit2)
    else:
        account.balance = potential_balance
        session.add(account)
        deposit = Deposit(account_number=account.account_number, amount=body.amount)
        session.add(deposit)
        deposits.append(deposit)
    session.commit()

    for deposit in deposits:
        session.refresh(deposit)

    return deposits

@router.get("/", response_model=List[Deposit], tags=['deposit'])
def read_deposit(user: User = Depends(get_user), session: Session = Depends(get_session)):
    accounts = session.exec(select(Account).where(Account.user_id == user.id, Account.isActive == True)).all()
    account_numbers = [account.account_number for account in accounts]
    
    deposits = session.exec(select(Deposit).where(Deposit.account_number.in_(account_numbers))).all()
    return deposits