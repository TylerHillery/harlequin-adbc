import pytest
from harlequin.adapter import HarlequinCursor
from harlequin.catalog import Catalog, CatalogItem
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from harlequin_adbc.adapter import HarlequinAdbcAdapter, HarlequinAdbcConnection
from textual_fastdatatable.backend import create_backend

CONN_STR = "postgres://admin:admin@localhost:5432/postgres"
DRIVER_TYPE = "postgresql"


def test_connect() -> None:
    conn = HarlequinAdbcAdapter(conn_str=(CONN_STR,), driver_type=DRIVER_TYPE).connect()
    assert isinstance(conn, HarlequinAdbcConnection)


def test_init_extra_kwargs() -> None:
    assert HarlequinAdbcAdapter(
        conn_str=(CONN_STR,),
        driver_type=DRIVER_TYPE,
        foo=1,
        bar="baz",
    ).connect()


def test_connect_raises_connection_error() -> None:
    with pytest.raises(HarlequinConnectionError):
        _ = HarlequinAdbcAdapter(
            conn_str=("foo",),
            driver_type=DRIVER_TYPE,
        ).connect()


@pytest.fixture
def connection() -> HarlequinAdbcConnection:
    return HarlequinAdbcAdapter(
        conn_str=(CONN_STR,),
        driver_type=DRIVER_TYPE,
    ).connect()


def test_get_catalog(connection: HarlequinAdbcConnection) -> None:
    catalog = connection.get_catalog()
    assert isinstance(catalog, Catalog)
    assert catalog.items
    assert isinstance(catalog.items[0], CatalogItem)


def test_execute_ddl(connection: HarlequinAdbcConnection) -> None:
    cur = connection.execute("create table foo (a int)")
    assert cur is not None
    data = cur.fetchall()
    assert not data


def test_execute_select(connection: HarlequinAdbcConnection) -> None:
    cur = connection.execute("select 1 as a")
    assert isinstance(cur, HarlequinCursor)
    assert cur.columns() == [("a", "##")]
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 1


def test_execute_select_dupe_cols(connection: HarlequinAdbcConnection) -> None:
    cur = connection.execute("select 1 as a, 2 as a, 3 as a")
    assert isinstance(cur, HarlequinCursor)
    assert len(cur.columns()) == 3
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 3
    assert backend.row_count == 1


def test_set_limit(connection: HarlequinAdbcConnection) -> None:
    cur = connection.execute("select 1 as a union all select 2 union all select 3")
    assert isinstance(cur, HarlequinCursor)
    cur = cur.set_limit(2)
    assert isinstance(cur, HarlequinCursor)
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 2


def test_execute_raises_query_error(connection: HarlequinAdbcConnection) -> None:
    with pytest.raises(HarlequinQueryError):
        _ = connection.execute("selec;")
