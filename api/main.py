from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from api import mongo_repo, mysql_repo
from api.db_routes import build_router
from api.errors import StoreError


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    mongo_repo.close()


app = FastAPI(
    title="Olist Time-Series API",
    description=(
        "CRUD for customers, products, orders, and order items in MySQL and MongoDB, "
        "plus latest-record and date-range queries. Date ranges are inclusive of "
        "start_date and end_date. Daily sales exclude canceled and unavailable orders "
        "and sum item prices only. POST /demo/seed inserts matching demo rows in both databases."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(build_router("mysql", mysql_repo))
app.include_router(build_router("mongo", mongo_repo))


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
def health() -> dict:
    mysql_ok, mysql_detail = mysql_repo.ping_detail()
    mongo_ok, mongo_detail = mongo_repo.ping_detail()
    return {
        "mysql": mysql_ok,
        "mongodb": mongo_ok,
        "mysql_detail": mysql_detail,
        "mongodb_detail": mongo_detail,
    }


@app.post("/demo/seed", tags=["meta"])
def seed_demo() -> dict:
    """Insert demo customer, product, order, and item into both databases if missing."""
    try:
        mysql_result = mysql_repo.seed_demo()
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=f"MySQL seed failed: {exc.message}") from exc
    try:
        mongo_result = mongo_repo.seed_demo()
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=f"MongoDB seed failed: {exc.message}") from exc
    return {"mysql": mysql_result, "mongo": mongo_result}
