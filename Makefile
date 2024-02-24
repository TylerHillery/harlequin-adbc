.PHONY: check
check:
	pre-commit run --all-files

.PHONY: serve-postgres
serve-postgres:
	harlequin -P None -a adbc "postgres://admin:admin@localhost:5432/postgres" --driver-type postgresql --db-kwargs-str "autocommit=true"

.PHONY: serve-flightsql
serve-flightsql:
	harlequin -P None -a adbc "grpc+tls://localhost:31337" --driver-type flightsql --db-kwargs-str "username=flight_username;password=flight_password;adbc.flight.sql.client_option.tls_skip_verify=true"

.PHONY: serve-snowflake
serve-snowflake:
	harlequin -P None -a adbc "$SNOWFLAKE_URI" --driver-type snowflake

.PHONY: serve-sqlite
serve-sqlite:
	harlequin -P None -a adbc ":memory:" --driver-type sqlite
