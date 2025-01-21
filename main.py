from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, get_session
from route.auth import router as auth_router
from route.deposit import router as deposit_router
from route.transactions import router as trans_router, complete_pending_transaction
from route.account import router as account_router
from route.users import router as users_router
from sqlmodel import Session, select
from models import Transaction

app = FastAPI()

# Configuration CORS
origins = [
    "http://localhost:3000",  
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    session: Session = next(get_session())
    pending_transactions = session.exec(select(Transaction).where(Transaction.status == 1)).all()
    for transaction in pending_transactions:
        await complete_pending_transaction(transaction, session)

app.include_router(auth_router, prefix="/auth")
app.include_router(deposit_router, prefix="/deposit")
app.include_router(trans_router, prefix="/transactions")
app.include_router(account_router, prefix="/accounts")
app.include_router(users_router, prefix="/users")