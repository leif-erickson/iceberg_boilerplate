"""Emit OpenLineage run events for non-dbt pipeline steps (bronze SQL, GX)."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent, RunState

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = "datalake-etl"


def lineage_enabled() -> bool:
    if os.environ.get("OPENLINEAGE_DISABLED", "").lower() == "true":
        return False
    return bool(
        os.environ.get("OPENLINEAGE_URL")
        or os.environ.get("OPENLINEAGE_CONFIG")
        or os.environ.get("OPENLINEAGE__TRANSPORT__TYPE")
    )


def _client() -> OpenLineageClient:
    config_path = os.environ.get("OPENLINEAGE_CONFIG")
    if config_path and not Path(config_path).is_absolute():
        config_path = str(ROOT / config_path)
        os.environ["OPENLINEAGE_CONFIG"] = config_path
    log_dir = ROOT / "lineage"
    log_dir.mkdir(parents=True, exist_ok=True)
    return OpenLineageClient()


def _emit(
    client: OpenLineageClient,
    *,
    state: RunState,
    run_id: str,
    job_name: str,
    inputs: list[str],
    outputs: list[str],
) -> None:
    namespace = os.environ.get("OPENLINEAGE_NAMESPACE", "datalake-etl")
    ds_namespace = os.environ.get("OPENLINEAGE_DATASET_NAMESPACE", "lake")
    event = RunEvent(
        eventType=state,
        eventTime=datetime.now(timezone.utc).isoformat(),
        producer=PRODUCER,
        run=Run(runId=run_id),
        job=Job(namespace=namespace, name=job_name),
        inputs=[InputDataset(namespace=ds_namespace, name=i) for i in inputs],
        outputs=[OutputDataset(namespace=ds_namespace, name=o) for o in outputs],
    )
    client.emit(event)


@contextmanager
def lineage_run(
    job_name: str,
    *,
    inputs: list[str],
    outputs: list[str],
) -> Iterator[str]:
    """Context manager: emit START/COMPLETE or START/FAIL around a pipeline step."""
    if not lineage_enabled():
        yield ""
        return

    client = _client()
    run_id = str(uuid.uuid4())
    _emit(
        client,
        state=RunState.START,
        run_id=run_id,
        job_name=job_name,
        inputs=inputs,
        outputs=outputs,
    )
    try:
        yield run_id
        _emit(
            client,
            state=RunState.COMPLETE,
            run_id=run_id,
            job_name=job_name,
            inputs=inputs,
            outputs=outputs,
        )
    except Exception:
        _emit(
            client,
            state=RunState.FAIL,
            run_id=run_id,
            job_name=job_name,
            inputs=inputs,
            outputs=outputs,
        )
        raise


def set_parent_run_env(run_id: str) -> None:
    """Expose parent run id for nested emitters (e.g. dbt-ol)."""
    if run_id:
        os.environ["OPENLINEAGE_PARENT_RUN_ID"] = run_id
        os.environ["OPENLINEAGE_PARENT_JOB_NAMESPACE"] = os.environ.get(
            "OPENLINEAGE_NAMESPACE", "datalake-etl"
        )
        os.environ["OPENLINEAGE_PARENT_JOB_NAME"] = "medallion.pipeline"
