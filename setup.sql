-- login to PostgreSQL with ``sudo -u postgres psql''
create user admin with encrypted password 'woodland';
create user viewer with encrypted password ';AI1MJhvl_5JE710';
create user contributor with encrypted password 'qAkW5D2!kOrHp-bj';
create database seaice with owner admin;
-- now run 'sea --init-db'. This will create the schema, triggers, 
-- and tables, and grant the proper permissions to these users. 
