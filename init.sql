begin; 

create table if not exists term
(
  id integer not null, 
  termString text not null, 
  definition text not null, 
  examples text not null, 
  score integer not null,
  created timestamp not null, 
  modified timestamp not null, 
  primary key (id)
); 

commit; 
