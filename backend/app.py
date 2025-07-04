# uvicorn app:app --reload --host 0.0.0.0 --port 8000
from fastapi.middleware.cors import CORSMiddleware
import os, sys
from dotenv import load_dotenv
from models import *
from schemas import *
from databases import Database
from sqlalchemy import create_engine, select, update, insert
from sqlalchemy.orm import sessionmaker, Session
import bcrypt
import uuid
import traceback
import logging
logger = logging.getLogger("uvicorn.error")
from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Form,  Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
import numpy as np
import io
import os
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import face_recognition
import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml_models.person_detection_model.model import load_known_faces, safe_face_encodings
import json

# Load environment variables from .env.local
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env.local"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Create sync engine
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# Create tables if not exist 
metadata.create_all(engine)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
# Serve static files (e.g., signup.js)
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

# Configure templates directory
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "welcome to nimbus!"}

# store info on db
@app.post("/signup", response_model=UserResponse)
async def signup(
    name: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        # Read photo bytes & decode image
        img_bytes = await photo.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        bgr_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if bgr_img is None:
            raise HTTPException(status_code=400, detail="Invalid image uploaded.")

        # Convert to RGB for face_recognition
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

        # Detect and encode face
        face_locations = face_recognition.face_locations(rgb_img)
        encodings = face_recognition.face_encodings(rgb_img, face_locations)
        if not encodings:
            raise HTTPException(status_code=400, detail="Could not detect a face in the uploaded photo.")

        # Serialize the first 128-dim embedding as JSON string
        face_embedding = encodings[0].tolist()
        face_embedding_json = json.dumps(face_embedding)

        # Insert user into database
        result = db.execute(
            insert(users).values(
                name=name,
                face_embedding=face_embedding_json,
                balance=100.0,
            )
        )
        db.commit()
        user_id = result.inserted_primary_key[0]

        # Update in-memory embeddings for immediate recognition
        global KNOWN_ENCODINGS, KNOWN_NAMES
        KNOWN_ENCODINGS.append(np.array(face_embedding, dtype=float))
        KNOWN_NAMES.append(name)

        # Return the newly created user
        user = db.execute(select(users).where(users.c.user_id == user_id)).fetchone()
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")
        return UserResponse(**dict(user._mapping))

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

# Sign user check their balance from db
@app.get("/signin")
async def signin(db: Session = Depends(get_db)):
    recognized_user_name = "thien"  # Replace with your face recognition logic

    user = db.query(users).filter_by(name=recognized_user_name).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_name": user.name,
        "balance": user.balance,
    }

def load_known_faces_from_db() -> tuple[list[np.ndarray], list[str]]:
    db: Session = SessionLocal()
    try:
        rows = db.execute(select(users.c.name, users.c.face_embedding)).all()
    finally:
        db.close()

    encodings, names = [], []
    for name, raw_json in rows:
        if not raw_json:
            continue
        try:
            arr = np.array(json.loads(raw_json), dtype=float)
            encodings.append(arr)
            names.append(name)
        except Exception as e:
            print(f"Could not parse embedding for {name}: {e}")
    return encodings, names

# Immediately after your app/config setup:
KNOWN_ENCODINGS, KNOWN_NAMES = load_known_faces_from_db()
@app.post("/pay", response_model=TransactionResponse)
async def pay(
    file: UploadFile = File(...),
    request_json: str = Form(...),
    db: Session = Depends(get_db),
):
    # 1) Read uploaded image
    img_bytes = await file.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    bgr_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr_img is None:
        raise HTTPException(status_code=400, detail="Invalid uploaded photo")

    # 2) Convert & detect face
    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_img)
    encodings = face_recognition.face_encodings(rgb_img, face_locations)
    if not encodings:
        raise HTTPException(status_code=400, detail="No face detected")

    encoding = encodings[0]

    # 3) Compare face embedding
    matches = face_recognition.compare_faces(KNOWN_ENCODINGS, encoding)
    if not any(matches):
        raise HTTPException(status_code=401, detail="Face not recognized")

    best_idx = int(np.argmin(face_recognition.face_distance(KNOWN_ENCODINGS, encoding)))
    recognized_name = KNOWN_NAMES[best_idx]
    # 4) Query DB for recognized user
    user = db.execute(
        select(users).where(users.c.name == recognized_name)
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Recognized user not found in DB")

    user_id = user.user_id  # Now we have secure user ID

    # 5) Parse PayRequest from form
    pay_request_data = json.loads(request_json)
    pay_request = PayRequest(**pay_request_data)

    # 6) Check balance
    if user.balance < pay_request.total_amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # 7) Update user balance
    new_balance = user.balance - pay_request.total_amount
    db.execute(
        update(users).where(users.c.user_id == user_id).values(balance=new_balance)
    )

    total_quantity = sum(item.quantity for item in pay_request.items)

    # 8) Record transaction
    result = db.execute(
        insert(user_transactions).values(
            user_id=user_id,
            amount = pay_request.total_amount,
            total_quantity=total_quantity,
            description=pay_request.description,
            balance=new_balance,
        )
    )
    transaction_id = result.inserted_primary_key[0]

    items_responses = []
    for item in pay_request.items:
        # a) Insert each item in transaction_items
        res = db.execute(
            insert(transaction_items).values(
                transaction_id=transaction_id,
                item_id=item.item_id,
                quantity=item.quantity,
                price=item.price,
            )
        )
        trans_item_id = res.inserted_primary_key[0]
        items_responses.append(TransactionItemResponse(
            transaction_item_id=trans_item_id,
            transaction_id=transaction_id,
            item_id=item.item_id,
            quantity=item.quantity,
            price=item.price,
        ))

        # b) Decrease quantity remaining in item_checklist
        existing_item = db.execute(
            select(item_checklist).where(item_checklist.c.item_id == item.item_id)
        ).fetchone()

        if not existing_item or existing_item.quantity_remaining < item.quantity:
            raise HTTPException(status_code=400, detail=f"Item {item.item_id} unavailable or insufficient stock")

        db.execute(
            update(item_checklist)
            .where(item_checklist.c.item_id == item.item_id)
            .values(quantity_remaining=existing_item.quantity_remaining - item.quantity)
        )

    db.commit()

    transaction = db.execute(
        select(user_transactions).where(user_transactions.c.transaction_id == transaction_id)
    ).fetchone()
    logger.info(f"{recognized_name} buys {total_quantity} items with ${transaction.amount}")
    return TransactionResponse(
        user_name = recognized_name,
        transaction_id=transaction.transaction_id,
        amount=transaction.amount,
        description=transaction.description,
        created_at=transaction.created_at,
        balance=transaction.balance,
        total_quantity=transaction.total_quantity,
        items=items_responses,
    )

@app.get("/users")
def get_all_users(db=Depends(get_db)):
    # SELECT * FROM users
    query = select(users)
    result = db.execute(query).mappings().all()


    # Convert result rows to dictionaries for JSON response
    users_list = [dict(row) for row in result]

    return {"users": users_list}

@app.get("/test")
def test():
    logger.info("Test endpoint was called!")
    return {"message": "Test successful"}
# CORS middleware settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("../ml_models/grocery-detection-model/run/train/grocery_finetune5/weights/best.pt")

# Inference-time filter: drop one class by index
unwanted_ids = [17, 19]

# build allowed list
allowed = [i for i in range(len(model.names)) if i not in unwanted_ids]

@app.get("/hello")
def read_hello():
    return "Hello World"


# detect groceries 
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Invalid image")

    # only run detection on classes in `allowed`
    results = model.predict(frame, conf=0.4, iou=0.5, classes=allowed)
    res = results[0]

    # annotate & return
    annotated = res.plot()
    _, encoded = cv2.imencode(".jpg", annotated)
    return StreamingResponse(io.BytesIO(encoded.tobytes()), media_type="image/jpeg")

@app.get("/signup", response_class=HTMLResponse)
@app.get("/signup/", response_class=HTMLResponse)
async def get_signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})
