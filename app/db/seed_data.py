import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import Base, SessionLocal, engine
from app.db.models import PipelineRun


logger = get_logger(__name__)
settings = get_settings()


REQUIRED_COLUMNS = {
    "run_id",
    "pipeline_name",
    "business_domain",
    "environment",
    "source_system",
    "target_system",
    "orchestrator",
    "job_name",
    "status",
    "attempt",
    "scheduled_time",
    "start_time",
    "end_time",
    "duration_seconds",
    "records_read",
    "records_written",
    "records_rejected",
    "data_quality_status",
    "sla_seconds",
    "sla_breach_seconds",
    "error_code",
    "error_category",
    "owner_team",
    "region",
    "correlation_id",
    "incident_id",
    "recovery_action",
}


def parse_datetime(value: str):
    if not value:
        return None

    return datetime.fromisoformat(value)


def validate_csv_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise ValueError("CSV file does not contain a header row.")

    missing_columns = REQUIRED_COLUMNS.difference(fieldnames)

    if missing_columns:
        raise ValueError(
            f"CSV file is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def seed_pipeline_runs(file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Seed data file not found: {file_path}"
        )

    Base.metadata.create_all(bind=engine)

    inserted_count = 0
    skipped_count = 0

    with file_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        validate_csv_columns(reader.fieldnames)

        with SessionLocal() as session:

            try:
                for row in reader:

                    existing_run = session.scalar(
                        select(PipelineRun).where(
                            PipelineRun.run_id == row["run_id"]
                        )
                    )

                    if existing_run:
                        skipped_count += 1
                        continue

                    pipeline_run = PipelineRun(
                        run_id=row["run_id"],
                        pipeline_name=row["pipeline_name"],
                        business_domain=row["business_domain"],
                        environment=row["environment"],
                        source_system=row["source_system"],
                        target_system=row["target_system"],
                        orchestrator=row["orchestrator"],
                        job_name=row["job_name"],
                        status=row["status"],
                        attempt=int(row["attempt"]),
                        scheduled_time=parse_datetime(
                            row["scheduled_time"]
                        ),
                        start_time=parse_datetime(
                            row["start_time"]
                        ),
                        end_time=parse_datetime(
                            row["end_time"]
                        ),
                        duration_seconds=int(
                            row["duration_seconds"]
                        ),
                        records_read=int(
                            row["records_read"]
                        ),
                        records_written=int(
                            row["records_written"]
                        ),
                        records_rejected=int(
                            row["records_rejected"]
                        ),
                        data_quality_status=row[
                            "data_quality_status"
                        ],
                        sla_seconds=int(
                            row["sla_seconds"]
                        ),
                        sla_breach_seconds=int(
                            row["sla_breach_seconds"]
                        ),
                        error_code=row["error_code"] or None,
                        error_category=(
                            row["error_category"] or None
                        ),
                        owner_team=row["owner_team"],
                        region=row["region"],
                        correlation_id=row["correlation_id"],
                        incident_id=row["incident_id"] or None,
                        recovery_action=(
                            row["recovery_action"] or None
                        ),
                    )

                    session.add(pipeline_run)
                    inserted_count += 1

                session.commit()

            except Exception:
                session.rollback()
                logger.exception(
                    "Failed to seed pipeline run data."
                )
                raise

    logger.info(
        "Seed completed | inserted=%s | skipped=%s",
        inserted_count,
        skipped_count,
    )


if __name__ == "__main__":
    seed_pipeline_runs(
        Path(settings.seed_data_path)
    )