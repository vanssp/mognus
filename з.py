"""
Мини-демо QueryBuilder: одна бизнес-задача → разный SQL под разные СУБД.
Запуск:
  python querybuilder_demo.py
"""
from __future__ import annotations
from dataclasses import dataclass, field

# ---------- ПЛОХО: так на собесе лучше не делать ----------
def bad_sql(region: str, d1: str, d2: str) -> str:
    # Пользовательский ввод вклеен в строку → SQL injection / поломка кавычек
    return (
        f"SELECT day, SUM(amount) FROM sales "
        f"WHERE region = '{region}' AND day BETWEEN '{d1}' AND '{d2}' "
        f"GROUP BY day ORDER BY day LIMIT 100"
    )


# ---------- ХОРОШО: AST + Dialect ----------
@dataclass
class Query:
    """Что хотим получить — без привязки к диалекту БД."""
    select: list[str]
    table: str
    filters: dict[str, object] = field(default_factory=dict)
    group_by: list[str] = field(default_factory=list)
    order_by: list[str] = field(default_factory=list)
    limit: int | None = None


class Dialect:
    name = "base"
    def render(self, q: Query) -> tuple[str, dict]:
        raise NotImplementedError

    def _where(self, filters: dict[str, object]) -> tuple[str, dict]:
        """WHERE только через bind-параметры, не через f-string значений."""
        if not filters:
            return "", {}
        parts = []
        params: dict = {}
        # region
        if "region" in filters:
            parts.append("region = :region")
            params["region"] = filters["region"]
        # date range
        if "d1" in filters and "d2" in filters:
            parts.append("day BETWEEN :d1 AND :d2")
            params["d1"] = filters["d1"]
            params["d2"] = filters["d2"]
        return (" WHERE " + " AND ".join(parts)) if parts else "", params


class PostgresDialect(Dialect):
    name = "postgres"
    def render(self, q: Query) -> tuple[str, dict]:
        where_sql, params = self._where(q.filters)
        sql = (
            f"SELECT {', '.join(q.select)} FROM {q.table}"
            f"{where_sql}"
            + (f" GROUP BY {', '.join(q.group_by)}" if q.group_by else "")
            + (f" ORDER BY {', '.join(q.order_by)}" if q.order_by else "")
            + (f" LIMIT {q.limit}" if q.limit is not None else "")
        )
        return sql, params


class OracleDialect(Dialect):
    name = "oracle"
    def render(self, q: Query) -> tuple[str, dict]:
        where_sql, params = self._where(q.filters)
        # В Oracle вместо LIMIT — FETCH FIRST ... ROWS ONLY
        sql = (
            f"SELECT {', '.join(q.select)} FROM {q.table}"
            f"{where_sql}"
            + (f" GROUP BY {', '.join(q.group_by)}" if q.group_by else "")
            + (f" ORDER BY {', '.join(q.order_by)}" if q.order_by else "")
            + (f" FETCH FIRST {q.limit} ROWS ONLY" if q.limit is not None else "")
        )
        return sql, params
class ClickHouseDialect(Dialect):
    name = "clickhouse"
    def render(self, q: Query) -> tuple[str, dict]:
        where_sql, params = self._where(q.filters)
        # Для демо почти как Postgres, но представим другую функцию агрегации
        select = [s.replace("SUM(amount)", "sum(amount)") for s in q.select]
        sql = (
            f"SELECT {', '.join(select)} FROM {q.table}"
            f"{where_sql}"
            + (f" GROUP BY {', '.join(q.group_by)}" if q.group_by else "")
            + (f" ORDER BY {', '.join(q.order_by)}" if q.order_by else "")
            + (f" LIMIT {q.limit}" if q.limit is not None else "")
        )
        return sql, params

def build_sales_by_day(region: str, d1: str, d2: str) -> Query:
    """Бизнес-слой: одна и та же задача для любой БД."""
    return Query(
        select=["day", "SUM(amount) AS sum_amount"],
        table="sales",
        filters={"region": region, "d1": d1, "d2": d2},
        group_by=["day"],
        order_by=["day"],
        limit=100,
    )


if __name__ == "__main__":
    region = "Юг"
    # Злой ввод: пытается сломать SQL. В bad_sql — опасно. В Query — просто значение параметра.
    evil = "Юг'; DROP TABLE sales;--"
    print("=== ПЛОХО (f-string) ===")
    print(bad_sql(evil, "2026-01-01", "2026-01-31"))
    print()
    q = build_sales_by_day(evil, "2026-01-01", "2026-01-31")
    for dialect in (PostgresDialect(), OracleDialect(), ClickHouseDialect()):
        sql, params = dialect.render(q)
        print(f"=== {dialect.name.upper()} ===")
        print(sql)
        print("params:", params)
        print()