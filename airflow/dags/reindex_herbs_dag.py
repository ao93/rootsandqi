"""
DAG: reindex_herb_knowledge_base

Validates the RootsAndQi herb knowledge base (app/data/herbs.json) and, if
validation passes, re-indexes it into Qdrant.

Tasks:
    validate_herbs_data -> index_herbs

If validation fails, the DAG run fails at the validation step and indexing
does not run - Qdrant keeps its previous (last-known-good) index.

Schedule: daily by default. Can also be triggered manually from the Airflow UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pendulum
from airflow.decorators import dag, task

# The RootsAndQi app package is mounted into the Airflow container at
# /opt/airflow/rootsandqi (see docker-compose.yaml). Add it to sys.path so
# `app.services.herb_retriever` is importable from within DAG tasks.
PROJECT_ROOT = Path("/opt/airflow/rootsandqi")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dag(
    dag_id="reindex_herb_knowledge_base",
    description="Validate herbs.json and re-index it into Qdrant",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["rootsandqi", "mlops", "qdrant"],
)
def reindex_herb_knowledge_base():

    @task
    def validate_herbs_data() -> dict:
        """
        Validate app/data/herbs.json: schema, syndrome values, duplicate IDs.
        Raises (failing the task) if validation fails.
        """
        from app.services.herb_retriever import validate_herbs_data as _validate

        result = _validate()
        print(f"Validation passed: {result}")
        return result

    @task
    def index_herbs(validation_result: dict) -> int:
        """
        Re-index herbs.json into Qdrant. Only runs if validation succeeded.
        """
        from app.services.herb_retriever import index_herbs as _index

        count = _index()
        print(f"Indexed {count} herbs into Qdrant.")
        return count

    index_herbs(validate_herbs_data())


reindex_herb_knowledge_base()
