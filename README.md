# harlequin-adapter-template
This repo provides a template you can use to accelerate development of a new [Harlequin](https://harlequin.sh) database adapter.

For an in-depth guide on writing your own adapter, see the [Harlequin Docs](https://harlequin.sh/docs/contributing/adapter-guide).


## ADBC Bugs
- Snowflake adbc driver seems to be the only driver that returns the `xdbc_data_type` from `adbc_get_objects()`
- Snowflake adbc driver has a bug with `adbc_get_table_schema()` that returns `adbc_driver_manager.OperationalError: IO: sql: expected 12 destination arguments in Scan, not 11`
- The PostgreSQL adbc driver is overall buggy and when executing queries you might get the error `IO: [libpq] Fetch header failed: no COPY in progress`  
- SQLite and DuckDB don't have the same level of `depth` for `adbc_get_objects()` compared to other dbs which causes weird issues 
- DuckDB driver uses different names for the `adbc_get_objects()` which causes things to break