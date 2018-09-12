CREATE DATABASE seaice WITH OWNER = 'postgres';

CREATE USER contributor WITH ENCRYPTED PASSWORD 'PASS';

CREATE USER SeaIce;

\connect seaice

-- Create SI schema.
CREATE SCHEMA SI;

-- Create Users table if it doesn't exist.
CREATE TABLE IF NOT EXISTS SI.Users
        (
          id           SERIAL PRIMARY KEY NOT NULL,
          authority    VARCHAR(64) NOT NULL, 
          auth_id      VARCHAR(64) NOT NULL, 
          email        VARCHAR(64) NOT NULL, 
          last_name    VARCHAR(64) NOT NULL,
          first_name   VARCHAR(64) NOT NULL,
          reputation   INTEGER default 1 NOT NULL,
          enotify      BOOLEAN default true, 
          super_user   BOOLEAN default false, 
          UNIQUE (email)
        );
      ALTER SEQUENCE SI.Users_id_seq RESTART WITH 1001;
ALTER TABLE SI.Users ADD COLUMN IF NOT EXISTS orcid VARCHAR(64);

-- Create Terms table if it doesn't exist.
-- `concept_id` is a token provided by a third party service
-- to redirect permanently to a YAMZ term. `persistent_id` is
-- its URI.
CREATE TYPE SI.Class AS ENUM ('vernacular', 'canonical', 'deprecated');
CREATE TABLE IF NOT EXISTS SI.Terms
	(id         SERIAL PRIMARY KEY NOT NULL,
	owner_id    INTEGER DEFAULT 0 NOT NULL,
	created     TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	modified    TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	term_string TEXT NOT NULL,
	definition  TEXT NOT NULL,
	examples    TEXT NOT NULL,
	concept_id  VARCHAR(64) DEFAULT NULL, UNIQUE (concept_id),
	persistent_id  TEXT, UNIQUE (persistent_id),
	CHECK (persistent_id <> ''),

	up         INTEGER DEFAULT 0 NOT NULL,
	down       INTEGER DEFAULT 0 NOT NULL,
    consensus  FLOAT DEFAULT 0 NOT NULL,
	class SI.Class DEFAULT 'vernacular' NOT NULL,

    U_sum     INTEGER DEFAULT 0 NOT NULL,
    D_sum     INTEGER DEFAULT 0 NOT NULL,
    T_last    TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    T_stable  TIMESTAMP WITH TIME ZONE DEFAULT now(),

    tsv tsvector,
    FOREIGN KEY (owner_id) REFERENCES SI.Users(id)
    );
ALTER SEQUENCE SI.Terms_id_seq RESTART WITH 1001;
CREATE INDEX IF NOT EXISTS lower_term_string ON SI.Terms (LOWER(term_string));

-- Create Comments table if it doesn't exist.
CREATE TABLE IF NOT EXISTS SI.Comments
(
	id        SERIAL PRIMARY KEY NOT NULL,
    owner_id  INTEGER DEFAULT 0 NOT NULL,
   	term_id   INTEGER DEFAULT 0 NOT NULL,
	created   TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	modified  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	comment_string TEXT NOT NULL,
	FOREIGN kEY (owner_id) REFERENCES SI.Users(id),
 	FOREIGN KEY (term_id) REFERENCES SI.Terms(id) ON DELETE CASCADE
);
ALTER SEQUENCE SI.Comments_id_seq RESTART WITH 1001;

-- Create Tracking table if it doesn't exist. This table keeps
-- track of the terms users have starred as well as their vote
-- (+1 or -1). If they haven't voted, then vote = 0. This
-- implies a rule: if a user untracks a term, then his or her
-- vote is removed.
CREATE TABLE IF NOT EXISTS SI.Tracking
(
    user_id        INTEGER NOT NULL,
    term_id        INTEGER NOT NULL,
    vote INTEGER   DEFAULT 0 NOT NULL,
    star BOOLEAN   DEFAULT true NOT NULL,

    UNIQUE (user_id, term_id),
    FOREIGN KEY (user_id) REFERENCES SI.Users(id) ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES SI.Terms(id) ON DELETE CASCADE
);

-- Create schema and table for notifications.
CREATE SCHEMA SI_Notify;
CREATE TYPE SI_Notify.Class AS ENUM ('Base', 'Comment', 'TermUpdate', 'TermRemoved');

CREATE TABLE SI_Notify.Notify
(
    user_id      INTEGER not null,
    class        SI_notify.class not null,
    T            TIMESTAMP WITH TIME ZONE not null,
    term_id      INTEGER,
    from_user_id INTEGER,
    term_string  TEXT,
    enotified    BOOLEAN default false,
    FOREIGN KEY (user_id) REFERENCES SI.Users(id) on DELETE CASCADE,
    FOREIGN KEY (from_user_id) REFERENCES SI.Users(id) on DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES SI.Terms(id) on DELETE CASCADE
);

GRANT USAGE ON SCHEMA SI, SI_Notify to contributor;

GRANT SELECT, UPDATE, DELETE ON ALL TABLES IN SCHEMA SI, SI_Notify to contributor;

-- Create update triggers.
CREATE OR REPLACE FUNCTION SI.upd_timestamp() RETURNS TRIGGER
	language plpgsql
	as
      $$
	    begin
          new.modified = current_timestamp;
	      return new;
        end;
      $$;

CREATE TRIGGER term_update
	before update of term_string, definition, examples on SI.Terms
    for each row
    	execute procedure SI.upd_timestamp();

CREATE TRIGGER comment_update
	before update on SI.Comments
    for each row
    	execute procedure SI.upd_timestamp();

CREATE TRIGGER tsv_update
	before insert or update on SI.Terms
    for each row execute procedure
    	tsvector_update_trigger(tsv, 'pg_catalog.english', term_string, definition, examples);