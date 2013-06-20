-- login to PostgreSQL with ``sudo -u postgres psql''
create user admin with encrypted password 'PASS';
create user viewer with encrypted password 'PASS';
create user contributor with encrypted password 'PASS';
create database seaice with owner admin;
-- now run 'sea --init-db'. This will create the schema, triggers, 
-- and tables, and grant the proper permissions to these users. 
