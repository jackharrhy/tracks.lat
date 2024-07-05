BEGIN;

ALTER TABLE tracks DROP CONSTRAINT tracks_pkey;

ALTER TABLE tracks ADD COLUMN id SERIAL PRIMARY KEY;

ALTER TABLE tracks ADD CONSTRAINT tracks_user_id_slug_key UNIQUE (user_id, slug);

COMMIT;
