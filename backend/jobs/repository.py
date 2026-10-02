import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Text,
    select,
    insert,
    update,
    func,
)
from backend.jobs.models import Job


class JobRepository:
    def __init__(self, db_url: str = "sqlite:///jobs.db"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.jobs_table = Table(
            "jobs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("source", String, nullable=False),
            Column("source_job_id", String, nullable=False),
            Column("company", String),
            Column("title", String),
            Column("location", String),
            Column("work_mode", String),
            Column("job_url", String, nullable=False),
            Column("application_url", String),
            Column("description", Text),
            Column("posted_date", String),
            Column("closing_date", String),
            Column("experience_requirement", String),
            Column("education_requirement", String),
            Column("required_skills", Text),
            Column("preferred_skills", Text),
            Column("eligibility", String),
            Column("compensation", String),
            Column("internship_information", String),
            Column("discovered_at", String, nullable=False),
            Column("updated_at", String),
            Column("raw_source_reference", Text),
        )
        self._create_tables()

    def _create_tables(self):
        self.metadata.create_all(self.engine)

    def _serialize_job(self, job: Job) -> dict:
        data = job.model_dump()
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, (list, dict)):
                data[k] = json.dumps(v) if v is not None else None
        return data

    def _deserialize_job(self, row) -> Job:
        data = dict(row._mapping)
        for k in ["posted_date", "closing_date", "discovered_at", "updated_at"]:
            if data.get(k):
                data[k] = datetime.fromisoformat(data[k])
        for k in ["required_skills", "preferred_skills"]:
            if data.get(k):
                data[k] = json.loads(data[k])
        if data.get("raw_source_reference"):
            data["raw_source_reference"] = json.loads(data["raw_source_reference"])

        return Job(**data)

    def upsert(self, job: Job) -> None:
        data = self._serialize_job(job)
        with self.engine.begin() as conn:
            stmt = select(self.jobs_table).where(self.jobs_table.c.id == job.id)
            existing = conn.execute(stmt).fetchone()

            if existing:
                upd_stmt = (
                    update(self.jobs_table)
                    .where(self.jobs_table.c.id == job.id)
                    .values(**data)
                )
                conn.execute(upd_stmt)
            else:
                ins_stmt = insert(self.jobs_table).values(**data)
                conn.execute(ins_stmt)

    def get_by_id(self, job_id: str) -> Optional[Job]:
        with self.engine.connect() as conn:
            stmt = select(self.jobs_table).where(self.jobs_table.c.id == job_id)
            row = conn.execute(stmt).fetchone()
            if row:
                return self._deserialize_job(row)
        return None

    def get_by_source_job_id(self, source: str, source_job_id: str) -> Optional[Job]:
        with self.engine.connect() as conn:
            stmt = select(self.jobs_table).where(
                self.jobs_table.c.source == source,
                self.jobs_table.c.source_job_id == source_job_id,
            )
            row = conn.execute(stmt).fetchone()
            if row:
                return self._deserialize_job(row)
        return None

    def get_all(self) -> List[Job]:
        with self.engine.connect() as conn:
            stmt = select(self.jobs_table)
            rows = conn.execute(stmt).fetchall()
            return [self._deserialize_job(row) for row in rows]

    def count(self) -> int:
        with self.engine.connect() as conn:
            stmt = select(func.count()).select_from(self.jobs_table)
            return conn.execute(stmt).scalar()
