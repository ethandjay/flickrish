DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS pictures;


create table users (
  username text,
  password text,
  id integer primary key autoincrement
);

create table pictures (
  imgpath text,
  title text,
  description text,
  owner text,
  id integer primary key autoincrement
);