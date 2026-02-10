from fastapi import FastAPI, Depends
from sqlmodel import create_engine, SQLModel, Session, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
import duckdb
import pyarrow as pa
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Note: For Python 3.14, use subinterpreters for better nogil perf: import _xxsubinterpreters
# Currently on 3.13 with PYTHON_GIL=0 for concurrency in I/O-bound tasks.

DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/db"
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

@app.get("/items", response_model=bytes)  # Arrow-based response for perf
async def get_items(session: AsyncSession = Depends(get_session)):
    # Async DB query
    result = await session.exec(select(Item))
    items = result.all()
    
    # Use DuckDB for in-memory processing (e.g., query/transform)
    con = duckdb.connect()
    df_arrow = con.from_arrow_table(pa.Table.from_pydict({"items": [i.dict() for i in items]}))  # Arrow table
    processed = con.execute("SELECT * FROM df_arrow").arrow()  # Example transform
    
    # Serialize to Arrow IPC stream for efficient API response
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, processed.schema) as writer:
        writer.write_table(processed)
    return sink.getvalue().to_pybytes()

# Example Minio integration (async upload arrow data)
from minio import Minio
import asyncio

minio_client = Minio("minio:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

async def upload_to_minio(data: bytes):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: minio_client.put_object("bucket", "data.arrow", data, len(data)))