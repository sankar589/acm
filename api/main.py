from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends, Body, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from schema.menu import Category, get_categories
from schema.token import Token, create_access_token, authenticate_access_token, authenticate_waiter_token
from schema.user import UserId, UserCreate, UserUpdate, create_user, update_user, authenticate_user_id, authenticate_user_mobile
from schema.order import CartItem, create_order, get_order, get_order_status, get_order_by_filter, update_order_status
from schema.database import ObjectId, database_connect, database_disconnect
from schema.waiter import authenticate_waiter
from schema.cors import origins

STATUS = ('placed', 'preparing', 'ready', 'served')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# User Authentication
# -------------------


@app.get("/user", response_model=UserId)
async def handle_get_user(id: Annotated[ObjectId, Depends(authenticate_user_mobile)]):
    return {"_id": id}


@app.post("/user", response_model=UserId)
async def handle_post_user(user_data: UserCreate):
    return await create_user(user_data)


@app.patch("/user", response_model=None)
async def handle_patch_user(id: Annotated[ObjectId, Depends(authenticate_access_token)], user_data: UserUpdate):
    result: tuple[int, int] = await update_user(id, user_data)

    match result:
        case (0, _):
            raise HTTPException(status_code=400, detail="Invalid id")
        case (_, 0):
            return {"message": "not modified"}
        case _:
            return {"message": "modified"}


@app.get("/user/token")
async def handle_get_user_token(id: Annotated[str, Depends(authenticate_access_token)]):
    return {"_id": id}


@app.post("/user/token", response_model=Token)
async def handle_post_user_token(id: Annotated[ObjectId, Depends(authenticate_user_id)]):
    return create_access_token({"_id": str(id)}, 'access')

# -------------------
# Waiter
# -------------------

@app.get("/waiter/token")
async def verify_token(id: Annotated[str, Depends(authenticate_waiter_token)]):
    return {"_id": id}


@app.post("/waiter/token", dependencies=[Depends(authenticate_waiter)], response_model=Token)
async def create_waiter_token():
    return create_access_token({"_id": "waiter"}, 'waiter')

# -------------------
# Menu
# -------------------

@app.get("/menu", response_model=list[Category])
async def fetch_categories():
    return await get_categories()

# -------------------
# Order
# -------------------

@app.post("/order")
async def handle_post_order(id: Annotated[str, Depends(authenticate_access_token)], items: list[CartItem], total: Annotated[int, Body()]):
    return await create_order(id, items, total)


@app.get("/order", response_model=None)
async def handle_get_order(id: Annotated[str, Depends(authenticate_access_token)]):
    return await get_order(id)


@app.get("/order/status", response_model=None)
async def handle_get_order_status(id: Annotated[str, Depends(authenticate_access_token)]):
    return await get_order_status(id)


@app.get("/order/filter", dependencies=[Depends(authenticate_waiter_token)], response_model=None)
async def handle_get_order_filter(filter: Annotated[str, Header()]):
    return await get_order_by_filter(filter)


@app.patch("/order/{id}", dependencies=[Depends(authenticate_waiter_token)], response_model=None)
async def handle_patch_order_by_id(id: int, status: Annotated[str, Header()]):
    result: tuple[int, int] = await update_order_status(id, status)

    match result:
        case (0, _):
            raise HTTPException(status_code=400, detail="Invalid id")
        case (_, 0):
            return {"message": "not modified"}
        case _:
            return {"message": "modified"}


app.mount('/image', StaticFiles(directory="image"), name="image")

app.add_event_handler("startup", database_connect)
app.add_event_handler("shutdown", database_disconnect)
