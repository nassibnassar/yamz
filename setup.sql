create user 'viewer'@'localhost' identified by 'PASSWORD';
grant select on seaice.* to 'viewer'@'localhost'; 

create user 'contributor'@'localhost' identified by 'PASSWORD';
grant select on seaice.* to 'contributor'@'localhost'; 
grant insert, update, delete on seaice.Terms, seaice.Relations, seaice.CommentHistory to 'contributor'@'localhost';
