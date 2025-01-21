import asyncio
from asyncio import sleep
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from models import Account, Transaction, User
from schemas import CreateTransaction
from route.auth import get_user

router = APIRouter()

async def complete_pending_transaction(transaction: Transaction, session: Session):
    if transaction.status == 1:
        transaction.status = 2
        session.add(transaction)

        receiver_account = session.exec(
            select(Account).where(Account.account_number == transaction.receiver_id)
        ).first()
        if receiver_account:
            receiver_account.balance += transaction.amount
            session.add(receiver_account)

            if not receiver_account.isMain and receiver_account.balance > 50000:
                receiver_user_id = receiver_account.user_id
                main_account = session.exec(
                    select(Account).where(Account.user_id == receiver_user_id, Account.isMain == True)
                ).first()

                if main_account:
                    excess_amount = receiver_account.balance - 50000
                    transaction2 = Transaction(
                        sender_id=receiver_account.account_number,
                        receiver_id=main_account.account_number,
                        amount=excess_amount,
                        status=2,
                        description="Automatic transfer of excess amount over 50,000"
                    )
                    main_account.balance += excess_amount
                    receiver_account.balance = 50000

                    session.add(receiver_account)
                    session.add(main_account)
                    session.add(transaction2)

        session.commit()

async def process_transaction(transaction_id: int, session: Session):
    await sleep(10)
    with session:
        transaction = session.get(Transaction, transaction_id)
        if transaction and transaction.status == 1:
            transaction.status = 2
            session.add(transaction)

            receiver_account = session.exec(
                select(Account).where(Account.account_number == transaction.receiver_id)
            ).first()
            if receiver_account:
                receiver_account.balance += transaction.amount
                session.add(receiver_account)

                if not receiver_account.isMain and receiver_account.balance > 50000:
                    receiver_user_id = receiver_account.user_id
                    main_account = session.exec(
                        select(Account).where(Account.user_id == receiver_user_id, Account.isMain == True)
                    ).first()

                    if main_account:
                        excess_amount = receiver_account.balance - 50000
                        transaction2 = Transaction(
                            sender_id=receiver_account.account_number,
                            receiver_id=main_account.account_number,
                            amount=excess_amount,
                            status=2,
                            description="Automatic transfer of excess amount over 50,000"
                        )
                        main_account.balance += excess_amount
                        receiver_account.balance = 50000

                        session.add(receiver_account)
                        session.add(main_account)
                        session.add(transaction2)

            session.commit()

@router.post("/", response_model=Transaction, tags=['transactions'])
async def create_transaction(
    body: CreateTransaction, 
    user: User = Depends(get_user), 
    session: Session = Depends(get_session)
) -> Transaction:
    sender_account = session.exec(
        select(Account).where(
            Account.user_id == user.id, 
            Account.account_number == body.sender_id, 
            Account.isActive == True
        )
    ).first()

    if sender_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    
    if sender_account.balance < body.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough money")

    if body.amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

    receiver_account = session.exec(
        select(Account).where(
            Account.account_number == body.receiver_id,
            Account.isActive == True
        )
    ).first()

    if receiver_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver account not found")

    sender_account.balance -= body.amount
    session.add(sender_account)
    transaction = Transaction(
        sender_id=body.sender_id,
        receiver_id=body.receiver_id,
        amount=body.amount,
        status=1,
        description=body.description  
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    asyncio.create_task(process_transaction(transaction.id, session))
    return transaction

@router.post("/{transaction_id}/cancel", response_model=Transaction, tags=['transactions'])
def cancel_transaction(transaction_id: int, user: User = Depends(get_user), session: Session = Depends(get_session)) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if transaction is None or transaction.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found or cannot be canceled")

    sender_account = session.exec(select(Account).where(Account.account_number == transaction.sender_id, Account.isActive == True)).first()
    if sender_account is None or sender_account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to cancel this transaction")

    sender_account.balance += transaction.amount
    session.add(sender_account)

    transaction.status = 0
    transaction.description = "Transaction canceled by user"
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

@router.get("/{transaction_id}/details", response_model=Transaction, tags=['transactions'])
def read_transactions(transaction_id: int, session: Session = Depends(get_session), user: User = Depends(get_user)):
    transaction = session.exec(select(Transaction).where(Transaction.id == transaction_id)).first()
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pas de transaction trouvé")
    transactionSender = transaction.sender_id
    transactionReceiver = transaction.receiver_id
    
    accountSender = session.exec(select(Account).where(Account.account_number == transactionSender)).first()
    accountReceiver = session.exec(select(Account).where(Account.account_number == transactionReceiver)).first()
    
    sender = accountSender.user_id
    receiver = accountReceiver.user_id
    
    if user.id != sender and user.id != receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vous n'avez pas accès à cette transaction")
    
    return transaction

@router.delete("/{transaction_id}", response_model=Transaction, tags=['transactions'])
def delete_transaction(transaction_id: int, user: User = Depends(get_user), session: Session = Depends(get_session)) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    sender_account = session.exec(select(Account).where(Account.account_number == transaction.sender_id, Account.isActive == True)).first()
    if sender_account is None or sender_account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this transaction")

    transaction.status = 0
    transaction.description = "Transaction deleted by user"
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction