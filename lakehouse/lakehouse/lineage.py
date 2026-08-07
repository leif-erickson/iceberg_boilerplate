"""OpenLineage emission for lakehouse stages.

Local runs append events to `lineage/events.ndjson` (via the OpenLineage file
transport in `openlineage.yml`). In prod, point `OPENLINEAGE_URL` at Marquez /
DataHub / OpenMetadata to build the lineage graph.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent, RunState

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCER = "lakehouse"


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
        os.environ["OPENLINEAGE_CONFIG"] = str(PROJECT_ROOT / config_path)
    (PROJECT_ROOT / "lineage").mkdir(parents=True, exist_ok=True)
    return OpenLineageClient()


def _emit(client: OpenLineageClient, state: RunState, run_id: str, job: str,
          inputs: list[str], outputs: list[str]) -> None:
    namespace = os.environ.get("OPENLINEAGE_NAMESPACE", "lakehouse")
    ds_namespace = os.environ.get("OPENLINEAGE_DATASET_NAMESPACE", "lake")
    client.emit(
        RunEvent(
            eventType=state,
            eventTime=datetime.now(timezone.utc).isoformat(),
            producer=PRODUCER,
            run=Run(runId=run_id),
            job=Job(namespace=namespace, name=job),
            inputs=[InputDataset(namespace=ds_namespace, name=i) for i in inputs],
            outputs=[OutputDataset(namespace=ds_namespace, name=o) for o in outputs],
        )
    )


@contextmanager
def lineage_run(job: str, *, inputs: list[str], outputs: list[str]) -> Iterator[str]:
    """Emit START/COMPLETE or START/FAIL around a pipeline step."""
    if not lineage_enabled():
        yield ""
        return
    client = _client()
    run_id = str(uuid.uuid4())
    _emit(client, RunState.START, run_id, job, inputs, outputs)
    try:
        yield run_id
        _emit(client, RunState.COMPLETE, run_id, job, inputs, outputs)
    except Exception:
        _emit(client, RunState.FAIL, run_id, job, inputs, outputs)
        raise
