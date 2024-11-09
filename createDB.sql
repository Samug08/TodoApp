
create table users (
    id text primary key,
    username text,
    pass text
);


create table todos (
    id integer primary key autoincrement,
    todo text,
    info text,
    shared TEXT,
    done BOOLEAN,
    user_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);





