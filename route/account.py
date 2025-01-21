from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models import User, Account, Deposit, Transaction
from schemas import CreateUser, CreateAccount, CreateDeposit, IncomeResponse
from database import get_session
from typing import List, Optional
from route.auth import get_user
import random

router = APIRouter()

def generate_unique_account_number(session: Session) -> str:
    while True:
        account_number = f"FR76 30044 00001 {random.randint(10000000000, 99999999999)} {random.randint(10, 99)}"
        existing_account = session.exec(select(Account).where(Account.account_number == account_number)).first()
        if existing_account is None:
            return account_number

@router.post("/", response_model=Account, tags=['account'])
def create_account(body: CreateAccount, user: User = Depends(get_user), session: Session = Depends(get_session)) -> Account:
    account_number = generate_unique_account_number(session)

    account = Account(
        user_id=user.id,  
        balance=0,
        account_number=account_number,  
        isActive=True,
        name=body.name,  
        type=body.type
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.get("/", response_model=List[Account], tags=['account'])
def read_accounts(user: User = Depends(get_user), session: Session = Depends(get_session)):
    accounts = session.exec(select(Account).where(Account.user_id == user.id, Account.isActive == True)).all()
    return accounts

@router.get("/{account_number}", response_model=Optional[Account], tags=['account'])
def read_account(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)):
    account = session.exec(select(Account).where(Account.account_number == account_number, Account.isActive == True, Account.user_id == user.id)).first()
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found or you do not have permission to access this account")
    return account

@router.post("/{account_number}/deactivate", tags=['account'])
def deactivate_account(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)):
    account = session.exec(select(Account).where(Account.account_number == account_number, Account.isActive == True, Account.user_id == user.id)).first()
    mainAccount = session.exec(select(Account).where(Account.user_id == user.id and Account.isMain == True)).first()

    transactions = session.exec(select(Transaction).where((Transaction.sender_id == account_number) | (Transaction.receiver_id == account_number), Transaction.status == 1)).all()

    if account.isMain == True:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impossible de desactiver votre compte principal")
    
    elif len(transactions) == 0:
        transaction = Transaction(
            sender_id=account_number,
            receiver_id=mainAccount.account_number,
            amount=account.balance,
            status=2,
            description="Automatic transfer of remaining balance upon deactivation"  # Description automatique
        )   
            
        mainAccount.balance += account.balance
        account.balance = 0

        account.isActive = False
        session.add(account)
        session.add(mainAccount)
        session.add(transaction)
        session.commit()
        return {"detail": "Compte desactivé avec succès"}
        
    elif account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Des transactions sont en cours")

@router.get("/{account_number}/transactions", response_model=List[Transaction], tags=['account'])
def read_transactions(account_number: str, session: Session = Depends(get_session), user: User = Depends(get_user)):
    account = session.exec(select(Account).where(Account.account_number == account_number)).first()
    accountOwner = account.user_id
    if accountOwner != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ce compte ne vous appartient pas")
    transactions = session.exec(select(Transaction).where((Transaction.sender_id == account_number) | (Transaction.receiver_id == account_number))).all()
    if transactions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune transactions")
    return transactions

@router.get("/{account_number}/income", response_model=List[IncomeResponse], tags=['account'])
def get_account_income(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)) -> List[IncomeResponse]:
    account = session.exec(
        select(Account).where(
            Account.account_number == account_number,
            Account.user_id == user.id,
            Account.isActive == True
        )
    ).first()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    deposits = session.exec(
        select(Deposit).where(Deposit.account_number == account_number)
    ).all()

    received_transactions = session.exec(
        select(Transaction).where(Transaction.receiver_id == account_number)
    ).all()

    income = [
        IncomeResponse(account_number=d.account_number, amount=d.amount, date=d.deposit_date, type="deposit", description=None)
        for d in deposits
    ] + [
        IncomeResponse(account_number=t.receiver_id, amount=t.amount, date=t.transaction_date, type="received_transaction", description=t.description)
        for t in received_transactions
    ]

    income.sort(key=lambda x: x.date)

    return income

@router.get("/{account_number}/expenses", response_model=List[Transaction], tags=['account'])
def get_account_expenses(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)) -> List[Transaction]:
    account = session.exec(
        select(Account).where(
            Account.account_number == account_number,
            Account.user_id == user.id,
            Account.isActive == True
        )
    ).first()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    sent_transactions = session.exec(
        select(Transaction).where(Transaction.sender_id == account_number).order_by(Transaction.transaction_date)
    ).all()

    return sent_transactions

@router.get("/{account_number}/all_transactions", response_model=List[IncomeResponse], tags=['account'])
def get_all_transactions(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)) -> List[IncomeResponse]:
    account = session.exec(
        select(Account).where(
            Account.account_number == account_number,
            Account.user_id == user.id,
            Account.isActive == True
        )
    ).first()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    deposits = session.exec(
        select(Deposit).where(Deposit.account_number == account_number)
    ).all()

    received_transactions = session.exec(
        select(Transaction).where(Transaction.receiver_id == account_number)
    ).all()

    sent_transactions = session.exec(
        select(Transaction).where(Transaction.sender_id == account_number)
    ).all()

    all_transactions = [
        IncomeResponse(account_number=d.account_number, amount=d.amount, date=d.deposit_date, type="deposit", description=None)
        for d in deposits
    ] + [
        IncomeResponse(account_number=t.receiver_id, amount=t.amount, date=t.transaction_date, type="received_transaction", description=t.description)
        for t in received_transactions
    ] + [
        IncomeResponse(account_number=t.sender_id, amount=t.amount, date=t.transaction_date, type="sent_transaction", description=t.description)
        for t in sent_transactions
    ]

    all_transactions.sort(key=lambda x: x.date, reverse=True)

    return all_transactions

@router.get("/{account_number}/account_know", response_model=List[str], tags=['account'])
def account_know_for_account(account_number: str, user: User = Depends(get_user), session: Session = Depends(get_session)):
    account = session.exec(select(Account).where(Account.account_number == account_number, Account.user_id == user.id)).first()
    
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found or you do not have permission to access this account")
    
    transactions = session.exec(select(Transaction).where(Transaction.sender_id == account_number)).all()
    
    recipient_account_numbers = {transaction.receiver_id for transaction in transactions}
    
    if not recipient_account_numbers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No transactions found for this account")
    
    return list(recipient_account_numbers)