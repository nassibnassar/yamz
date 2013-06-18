create user 'viewer'@'localhost' identified by 'fella';
grant select on seaice.* to 'viewer'@'localhost'; 
create user 'contributor'@'localhost' identified by 'guy';
grant select on seaice.* to 'contributor'@'localhost'; 
grant insert, update, delete on seaice.* to 'contributor'@'localhost';
