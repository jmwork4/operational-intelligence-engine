"""Row-Level Security policy generation and application."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# All tables that are scoped by tenant_id.
TENANT_SCOPED_TABLES: list[str] = [
    "users",
    "events",
    "resources",
    "processes",
    "transactions",
    "rules",
    "alerts",
    "documents",
    "document_chunks",
    "embeddings",
    "audit_logs",
]


def generate_rls_policies() -> list[str]:
    """Return a list of SQL statements that enable RLS on tenant-scoped tables.

    Each table gets:
      - ALTER TABLE ... ENABLE ROW LEVEL SECURITY
      - ALTER TABLE ... FORCE ROW LEVEL SECURITY
      - SELECT / INSERT / UPDATE / DELETE policies that restrict rows to the
        tenant identified by current_setting('app.current_tenant_id').
    """
    statements: list[str] = []

    for table in TENANT_SCOPED_TABLES:
        # Enable and force RLS
        statements.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        statements.append(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        # SELECT policy
        statements.append(
            f"CREATE POLICY tenant_isolation_select ON {table} "
            f"FOR SELECT USING ("
            f"current_setting('app.current_tenant_id')::uuid = tenant_id"
            f");"
        )

        # INSERT policy
        statements.append(
            f"CREATE POLICY tenant_isolation_insert ON {table} "
            f"FOR INSERT WITH CHECK ("
            f"current_setting('app.current_tenant_id')::uuid = tenant_id"
            f");"
        )

        # UPDATE policy
        statements.append(
            f"CREATE POLICY tenant_isolation_update ON {table} "
            f"FOR UPDATE USING ("
            f"current_setting('app.current_tenant_id')::uuid = tenant_id"
            f");"
        )

        # DELETE policy
        statements.append(
            f"CREATE POLICY tenant_isolation_delete ON {table} "
            f"FOR DELETE USING ("
            f"current_setting('app.current_tenant_id')::uuid = tenant_id"
            f");"
        )

    return statements


async def apply_rls_policies(session: AsyncSession) -> None:
    """Execute all RLS policy statements against the database."""
    for stmt in generate_rls_policies():
        await session.execute(text(stmt))
    await session.commit()
