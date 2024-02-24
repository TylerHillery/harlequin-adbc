from harlequin.options import (
    PathOption,
    SelectOption,
    TextOption,
)

driver_type = SelectOption(
    name="driver-type",
    description=("The driver database type"),
    choices=["flightsql", "postgresql", "snowflake", "sqlite", "duckdb"],
    default=None,
)

driver_path = PathOption(
    name="driver-path",
    description=(
        "The ADBC driver path, if not specified it will attempt to use the python"
        "version so make sure to install the necessary extra."
    ),
    resolve_path=True,
    exists=False,
    file_okay=True,
    dir_okay=False,
    default=None,
)

db_kwargs_str = TextOption(
    name="db-kwargs-str",
    description=(
        "Database connection parameters as key=value pairs, separated by commas. "
        "Example: --db-kwargs 'username=flight_username,password=flight_password'"
    ),
    default=None,
)

ADBC_OPTIONS = [driver_type, driver_path, db_kwargs_str]
