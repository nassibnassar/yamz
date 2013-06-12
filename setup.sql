create database seaice;
create user 'viewer'@'localhost' identified by 'PASSWORD';
grant select on seaice.* to 'viewer'@'localhost';
create user 'contributor'@'localhost' identified by 'PASSWORD';
grant insert, update, delete on seaice.* to 'contributor'@'localhost';


