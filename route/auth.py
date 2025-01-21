from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
import jwt
from models import User, Account, Deposit
from schemas import CreateUser, UserResponse, CreateAccount, CreateDeposit, LoginUser, ChangePassword, ChangeEmail
from database import get_session, engine
from sqlmodel import select, Session
import random

router = APIRouter()

secret_key = "very_secret_key"
algorithm = "HS256"
bearer_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_token(user: User):
    return jwt.encode({"id": user.id, "email": user.email}, secret_key, algorithm=algorithm)

def generate_unique_account_number(session: Session) -> str:
    while True:
        account_number = f"FR76 30044 00001 {random.randint(10000000000, 99999999999)} {random.randint(10, 99)}"
        existing_account = session.exec(select(Account).where(Account.account_number == account_number)).first()
        if existing_account is None:
            return account_number

def get_user(authorization: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload = jwt.decode(authorization.credentials, secret_key, algorithms=[algorithm])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        with Session(engine) as session:
            user = session.get(User, user_id)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.post("/login", tags=['auth'])
def login(user: LoginUser, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if db_user is None or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return {"token": generate_token(db_user)}

@router.post("/register", response_model=UserResponse, tags=['auth'])
def register(user: CreateUser, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    existing_username = session.exec(select(User).where(User.username == user.username)).first()
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password, username=user.username)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    account_number = generate_unique_account_number(session)
    
    account = Account(
        user_id=db_user.id,
        balance=0.0,  
        account_number=account_number, 
        isMain=True, 
        name="Compte courant",  
        type="compte-courant"
    )
    
    session.add(account)
    session.commit()
    session.refresh(account)
    
    amount = 100.0  
    
    deposit = Deposit(
        account_number=account_number,
        amount=amount 
    )

    account.balance += amount
    session.add(account)

    session.add(deposit)
    session.commit()
    session.refresh(deposit)

    return db_user

@router.get("/me", response_model=UserResponse, tags=['auth'])
def read_me(user: User = Depends(get_user)):
    return UserResponse(email=user.email, username=user.username)

@router.post("/change-password", tags=['auth'])
def change_password(data: ChangePassword, user: User = Depends(get_user), session: Session = Depends(get_session)):
    if not pwd_context.verify(data.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    
    user.hashed_password = pwd_context.hash(data.new_password)
    session.add(user)
    session.commit()
    return {"message": "Password changed successfully"}

@router.post("/change-email", tags=['auth'])
def change_email(data: ChangeEmail, user: User = Depends(get_user), session: Session = Depends(get_session)):
    if user.email != data.current_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current email is incorrect")
    
    if not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password is incorrect")
    
    existing_user = session.exec(select(User).where(User.email == data.new_email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user.email = data.new_email
    session.add(user)
    session.commit()
    return {"message": "Email changed successfully"}