BEGIN;

CREATE TABLE user_role (
    id TEXT PRIMARY KEY
);

INSERT INTO user_role (id) VALUES ('user');
INSERT INTO user_role (id) VALUES ('admin');

ALTER TABLE users ADD COLUMN role TEXT REFERENCES user_role (id);

COMMIT;
