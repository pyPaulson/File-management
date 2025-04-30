from datetime import timedelta
import os
import shutil
from typing import Annotated
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile  
from database import engine, SessionLocal 
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import models 
from security import ALGORITHM, SECRET_KEY, create_access_token, hash_password, verify_password, create_email_verification_token
from fastapi.security import OAuth2PasswordRequestForm 
from auth import get_current_user
from jose import JWTError, jwt
from fastapi.responses import FileResponse
from utils import send_email_verification



app = FastAPI()

models.Base.metadata.create_all(bind=engine)

class UserModel(BaseModel):
    username: str
    email: EmailStr
    password: str


def get_db():
       db = SessionLocal()
       try:
              yield db 
       finally:
              db.close()

       
db_dependency = Annotated[Session, Depends(get_db)]

@app.post("/signup")
def signup(user: UserModel, db: db_dependency):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)

    db_user = models.User(
        username=user.username,
        email=user.email,
        password=hashed_pw
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    token = create_email_verification_token(user.email)
    send_email_verification(user.email, token)

    return {"message": "User created successfully"}



@app.get("/verify-email")
def verify_email(token: str, db: db_dependency):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_verified = True
        db.commit()

        return {"message": "Email verified successfully!"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Token is invalid or expired")



@app.post("/login")
def login(db: db_dependency, form_data: OAuth2PasswordRequestForm = Depends()):
    
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=30)
    )

    return {"access_token": token, "token_type": "bearer"}



@app.get("/me")
def read_logged_in_user(current_user: models.User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email
    }



@app.post("/upload")
def upload_file(
     db: db_dependency,
    current_user: models.User = Depends(get_current_user),
    file: UploadFile = File(...),
):

     upload_dir = "uploads"
     os.makedirs(upload_dir, exist_ok=True)

     file_path = os.path.join(upload_dir, file.filename)

     with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

     file_record = models.File(
        filename=file.filename,
        file_type=file.content_type,
        file_path=file_path,
        uploaded_by=current_user.id
    )
   
     db.add(file_record)
     db.commit()
     db.refresh(file_record)

     return {
        "message": f"File '{file.filename}' uploaded successfully",
        "file_id": file_record.id
    }


@app.get("/files")
def list_files(db: db_dependency, current_user: models.User = Depends(get_current_user)):
    files = db.query(models.File).filter(models.File.uploaded_by == current_user.id).all()
    return files


@app.get("/files/{file_id}")
def get_file(file_id: int, db: db_dependency, current_user: models.User = Depends(get_current_user)):
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.uploaded_by == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return file


@app.get("/download/{file_id}")
def download_file(
    file_id: int,
    db: db_dependency,
    current_user: models.User = Depends(get_current_user),
):
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.uploaded_by == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type=file.file_type
    )


@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    db: db_dependency,
    current_user: models.User = Depends(get_current_user),
):
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.uploaded_by == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    db.delete(file)
    db.commit()

    return {"message": f"File '{file.filename}' deleted successfully."}

