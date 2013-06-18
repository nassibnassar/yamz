create user 'viewer'@'localhost' identified by 'fella';
grant select on seaice.* to 'viewer'@'localhost'; 
create user 'contributor'@'localhost' identified by 'guy';
grant select on seaice.* to 'contributor'@'localhost'; 
grant insert, update, delete on seaice.* to 'contributor'@'localhost';

-- login to PostgreSQL with ``sudo -u postgres psql''
create user root with password 'woodland';
create user viewer with password ';AI1MJhvl_5JE710';
create user contributor with password 'qAkW5D2!kOrHp-bj';
create database seaice with owner root;

