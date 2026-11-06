from sqlalchemy import text
from sqlalchemy.engine import Engine


def test_postgres_is_reachable(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1


def test_ledger_tables_are_present_after_migrations(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public'
                    """
                )
            )
        }

    assert {
        "users",
        "accounts",
        "financial_transactions",
        "ledger_accounts",
        "ledger_transactions",
        "ledger_entries",
        "idempotency_records",
        "audit_events",
    }.issubset(tables)


def test_append_only_triggers_are_installed(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        trigger_names = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT tgname
                    FROM pg_trigger
                    WHERE NOT tgisinternal
                      AND tgname IN (
                        'ledger_entries_no_update_delete',
                        'audit_events_no_update_delete'
                      )
                    """
                )
            )
        }

    assert trigger_names == {
        "ledger_entries_no_update_delete",
        "audit_events_no_update_delete",
    }
