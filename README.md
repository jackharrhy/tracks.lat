# tracks.lat

https://tracks.lat - lat/lon -> 🌐

## setting up

install:

- postgres 16 w/postgres, tutorial will setup via [docker](https://docs.docker.com/get-docker/)
- [python](https://www.python.org/), tested using 3.12
- [migrate](https://github.com/golang-migrate/migrate/tree/master)

create db:

```sh
docker compose up -d db
```

run migrations for creating database schema:

```
export POSTGRESQL_URL='postgres://postgres:password@localhost:5932/tracks.lat?sslmode=disable'
migrate -database ${POSTGRESQL_URL} -path db/migrations up
```

**TODO explain how to setup venv, run api**

create an admin user:

```
# enter virtual environment
python cli.py create-user username person@example.com password admin
```

## migrations

creating migrations

```
migrate create -ext sql -dir db/migrations -seq add_foo
```
