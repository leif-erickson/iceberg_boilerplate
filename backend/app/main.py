import os

from fastapi import FastAPI, Depends, Response
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
import duckdb
import pyarrow as pa
from prometheus_fastapi_instrumentator import Instrumentator

from app.models import Item

app = FastAPI()

# Note: For Python 3.14, use subinterpreters for better nogil perf: import _xxsubinterpreters
# Currently on 3.13 with PYTHON_GIL=0 for concurrency in I/O-bound tasks.

# Default target the Docker Compose service name; override with DATABASE_URL for
# native/local development (e.g. postgresql+asyncpg://user:password@localhost:5432/db).
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@postgres:5432/db"
)
engine = create_async_engine(DATABASE_URL, echo=True)

async def get_session() -> AsyncSession:
    async with AsyncSession(engine) as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health():
    return {"status": "healthy"}

ARROW_STREAM_MEDIA_TYPE = "application/vnd.apache.arrow.stream"

ITEM_SCHEMA = pa.schema(
    [
        ("id", pa.int64()),
        ("name", pa.string()),
        ("description", pa.string()),
    ]
)


@app.get("/items")
async def get_items(session: AsyncSession = Depends(get_session)) -> Response:
    # Async DB query.
    result = await session.exec(select(Item))
    items = result.all()

    # Build a typed Arrow table from the ORM rows (explicit schema keeps the
    # empty-result case valid instead of degrading to a null-typed column).
    arrow_table = pa.table(
        {
            "id": [item.id for item in items],
            "name": [item.name for item in items],
            "description": [item.description for item in items],
        },
        schema=ITEM_SCHEMA,
    )

    # Use DuckDB for in-memory processing (e.g. query/transform).
    con = duckdb.connect()
    con.register("items", arrow_table)
    processed = con.execute("SELECT * FROM items ORDER BY id").arrow()

    # Serialize to an Arrow IPC stream for an efficient binary API response.
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, processed.schema) as writer:
        writer.write_table(processed)
    return Response(
        content=sink.getvalue().to_pybytes(),
        media_type=ARROW_STREAM_MEDIA_TYPE,
    )

# Example Minio integration (async upload arrow data)
from minio import Minio
import asyncio
from io import BytesIO

# MINIO_URL may include a scheme (http://host:port); Minio() wants host:port + secure flag.
_minio_url = os.getenv("MINIO_URL", "http://minio:9000")
_minio_secure = _minio_url.startswith("https://")
_minio_endpoint = _minio_url.split("://", 1)[-1]

minio_client = Minio(
    _minio_endpoint,
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=_minio_secure,
)

async def upload_to_minio(data: bytes):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: minio_client.put_object("bucket", "data.arrow", BytesIO(data), len(data)),
    )