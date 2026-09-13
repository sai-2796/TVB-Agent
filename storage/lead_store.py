import json
import sqlite3
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from models.lead import Lead, QualificationStatus


class LeadStore:
    """SQLite-backed storage manager for candidates, qualified leads, and evidence logs."""

    def __init__(self, db_path: str = "tvb_leads.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create necessary tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    domain TEXT,
                    company_name TEXT,
                    qualification_status TEXT,
                    verified_executive_email TEXT,
                    payload_json TEXT,
                    created_at TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_metadata (
                    run_id TEXT PRIMARY KEY,
                    metadata_json TEXT,
                    created_at TEXT
                );
            """)
            conn.commit()

    def save_lead(self, lead: Lead) -> None:
        """Insert or replace a lead in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            payload = lead.model_dump_json()
            cursor.execute(
                """
                INSERT OR REPLACE INTO leads (
                    id, domain, company_name, qualification_status, verified_executive_email, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead.id,
                    lead.domain,
                    lead.company_name,
                    lead.qualification_status.value,
                    lead.verified_executive_email,
                    payload,
                    lead.created_at,
                ),
            )
            conn.commit()

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Fetch a single lead by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            if row:
                return Lead.model_validate_json(row["payload_json"])
            return None

    def list_qualified_leads(self) -> List[Lead]:
        """List all leads with status QUALIFIED."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload_json FROM leads WHERE qualification_status = ?",
                (QualificationStatus.QUALIFIED.value,),
            )
            rows = cursor.fetchall()
            return [Lead.model_validate_json(row["payload_json"]) for row in rows]

    def list_rejected_leads(self) -> List[Lead]:
        """List all leads with status UNQUALIFIED."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload_json FROM leads WHERE qualification_status = ?",
                (QualificationStatus.UNQUALIFIED.value,),
            )
            rows = cursor.fetchall()
            return [Lead.model_validate_json(row["payload_json"]) for row in rows]

    def list_all_leads(self) -> List[Lead]:
        """List all stored leads."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM leads")
            rows = cursor.fetchall()
            return [Lead.model_validate_json(row["payload_json"]) for row in rows]

    def save_run_metadata(self, run_id: str, metadata: Dict[str, Any], created_at: str) -> None:
        """Save pipeline execution run telemetry metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO run_metadata (run_id, metadata_json, created_at) VALUES (?, ?, ?)",
                (run_id, json.dumps(metadata), created_at),
            )
            conn.commit()

    def get_run_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Fetch pipeline run telemetry metadata by run_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata_json FROM run_metadata WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["metadata_json"])
            return None

    def list_all_runs(self) -> List[Dict[str, Any]]:
        """List all pipeline execution run telemetry records sorted by created_at desc."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata_json FROM run_metadata ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [json.loads(row["metadata_json"]) for row in rows]
