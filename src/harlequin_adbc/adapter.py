from __future__ import annotations

import importlib
import logging
from typing import Any, Sequence

import duckdb
import pyarrow
from harlequin import (
    HarlequinAdapter,
    HarlequinConnection,
    HarlequinCursor,
)
from harlequin.catalog import Catalog, CatalogItem
from harlequin.exception import (
    HarlequinConfigError,
    HarlequinConnectionError,
    HarlequinQueryError,
)
from textual_fastdatatable.backend import AutoBackendType

from harlequin_adbc.cli_options import ADBC_OPTIONS

logging.basicConfig(
    filename="harlequin_adbc_connection.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


class HarlequinAdbcCursor(HarlequinCursor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.cur = args[0]
        self._limit: int | None = None

    def columns(self) -> list[tuple[str, str]]:
        assert self.cur.description is not None
        return [
            (col[0], self._get_short_col_type(col[1].id))
            for col in self.cur.description
        ]

    def set_limit(self, limit: int) -> HarlequinAdbcCursor:
        self._limit = limit
        return self

    def fetchall(self) -> AutoBackendType:
        try:
            if self._limit is None:
                return self.cur.fetchallarrow()
            else:
                return self.cur.fetchmany(self._limit)
        except Exception as e:
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e

    @staticmethod
    def _get_short_col_type(arrow_data_type_id: int) -> str:
        MAPPING = {
            pyarrow.null().id: "nul",
            pyarrow.bool_().id: "t/f",
            pyarrow.int8().id: "##",
            pyarrow.int16().id: "##",
            pyarrow.int32().id: "##",
            pyarrow.int64().id: "##",
            pyarrow.uint8().id: "##",
            pyarrow.uint16().id: "##",
            pyarrow.uint32().id: "##",
            pyarrow.uint64().id: "##",
            pyarrow.float32().id: "#.#",
            pyarrow.float64().id: "#.#",
            pyarrow.decimal128(15, 2).id: "#.##",
            pyarrow.time32("s").id: "t",
            pyarrow.time64("ns").id: "t",
            pyarrow.timestamp("s").id: "dt",
            pyarrow.date32().id: "d",
            pyarrow.date64().id: "d",
            pyarrow.month_day_nano_interval().id: "mdn",
            pyarrow.binary().id: "010",
            pyarrow.string().id: "s",
            pyarrow.utf8().id: "s",
            pyarrow.large_binary(): "010",
            pyarrow.large_string().id: "s",
            pyarrow.large_utf8().id: "s",
        }
        return MAPPING.get(arrow_data_type_id, "?")


class HarlequinAdbcConnection(HarlequinConnection):
    def __init__(
        self,
        conn_str: Sequence[str],
        driver_path: str | None = None,
        driver_type: str | None = None,
        *_: any,
        init_message: str = "",
        options: dict[str, Any],
    ) -> None:
        self.init_message = init_message
        connect_kwargs = {}
        try:
            if driver_path:
                dbapi = importlib.import_module("adbc_driver_manager.dbapi")
                options["uri"] = conn_str[0]
                connect_kwargs = {
                    "driver": driver_path,
                    "db_kwargs": options,
                }
            else:
                dbapi = importlib.import_module(f"adbc_driver_{driver_type}.dbapi")
                if options:
                    connect_kwargs["db_kwargs"] = options

            if connect_kwargs:
                self.conn = dbapi.connect(conn_str[0], **connect_kwargs)
            else:
                self.conn = dbapi.connect(conn_str[0])

        except ImportError as e:
            raise ImportError(
                "If driver_path is not provided then you must import the required "
                f"driver: adbc_driver_{options['driver_type']}"
            ) from e
        except Exception as e:
            raise HarlequinConnectionError(
                msg=str(e), title="Harlequin could not connect to your database."
            ) from e

    def execute(self, query: str) -> HarlequinCursor | None:
        try:
            cur = self.conn.cursor()
            cur.execute(query)
        except Exception as e:
            cur.close()
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e
        else:
            if cur.description is not None:
                return HarlequinAdbcCursor(cur)
            else:
                cur.close()
                return None

    def get_catalog(self) -> Catalog:
        dbs = self.conn.adbc_get_objects().read_all()  # noqa: F841
        filtered_dbs = (
            duckdb.sql(
                "SELECT * FROM dbs WHERE catalog_name NOT IN ('template0', 'template1')"
            )
            .arrow()
            .to_pylist()
        )
        db_items: list[CatalogItem] = []
        for db in filtered_dbs:
            schema_items: list[CatalogItem] = []
            db_name = db["catalog_name"]
            for schema in db["catalog_db_schemas"]:
                schema_name = schema["db_schema_name"]
                rel_items: list[CatalogItem] = []
                for rel in schema["db_schema_tables"]:
                    rel_name = rel["table_name"]
                    rel_type = "v" if rel["table_type"].upper() == "VIEW" else "t"
                    col_items: list[CatalogItem] = []
                    for col in rel["table_columns"]:
                        col_name = col["column_name"]
                        col_dtype_id = col["xdbc_data_type"]
                        col_items.append(
                            CatalogItem(
                                qualified_identifier=f'"{db_name}"."{schema_name}"."{rel_name}"."{col_name}"',
                                query_name=f'"{col_name}"',
                                label=col_name,
                                type_label=HarlequinAdbcCursor._get_short_col_type(
                                    col_dtype_id
                                ),
                            )
                        )
                    rel_items.append(
                        CatalogItem(
                            qualified_identifier=f'"{db_name}"."{schema_name}"."{rel_name}"',
                            query_name=f'"{db_name}"."{schema_name}"."{rel_name}"',
                            label=rel_name,
                            type_label=rel_type,
                            children=col_items,
                        )
                    )
                schema_items.append(
                    CatalogItem(
                        qualified_identifier=f'"{db_name}"."{schema_name}"',
                        query_name=f'"{db_name}"."{schema_name}"',
                        label=schema_name,
                        type_label="s",
                        children=rel_items,
                    )
                )
            db_items.append(
                CatalogItem(
                    qualified_identifier=f'"{db_name}"',
                    query_name=f'"{db_name}"',
                    label=db_name,
                    type_label="db",
                    children=schema_items,
                )
            )
        return Catalog(items=db_items)


class HarlequinAdbcAdapter(HarlequinAdapter):
    ADAPTER_OPTIONS = ADBC_OPTIONS

    def __init__(
        self,
        conn_str: Sequence[str],
        driver_path: str | None = None,
        driver_type: str | None = None,
        db_kwargs_str: str | None = None,
        **_: Any,
    ) -> None:
        self.conn_str = conn_str 
        self.driver_path = driver_path
        self.driver_type = driver_type
        if len(self.conn_str) != 1:
            raise HarlequinConfigError(
                title="Harlequin could not initialize the ADBC adapter.",
                msg=(
                    "The ADBC adapter expects exactly one connection string. "
                    f"It received:\n{conn_str}"
                ),
            )
        if not self.driver_path and not self.driver_type:
            raise HarlequinConfigError(
                title="Harlequin could not initialize the ADBC adapter.",
                msg=(
                    "The ADBC adapter expects either at least a driver type or"
                    " a driver path and neither was provided."
                ),
            )
        self.options = self.parse_db_kwargs(db_kwargs_str) if db_kwargs_str else {}

    def connect(self) -> HarlequinAdbcConnection:
        conn = HarlequinAdbcConnection(
            self.conn_str,
            driver_path=self.driver_path,
            driver_type=self.driver_type,
            options=self.options,
        )
        return conn

    @staticmethod
    def parse_db_kwargs(db_kwargs_str: str) -> dict:
        kv_pairs = db_kwargs_str.split(";")
        return {k: v for k, v in (pair.split("=") for pair in kv_pairs)}
