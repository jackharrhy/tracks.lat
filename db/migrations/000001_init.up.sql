BEGIN;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE (username)
);

CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    geometry GEOMETRY(MULTILINESTRING, 4326) NOT NULL,
    activity TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE (user_id, slug)
);

COMMIT;
