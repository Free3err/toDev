CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    title VARCHAR(256),
    description TEXT,
    dir TEXT UNIQUE,
    logo INTEGER,
    state INTEGER
);

CREATE TABLE states (
    id INTEGER PRIMARY KEY,
    state VARCHAR(256)
);

CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    path TEXT
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title VARCHAR(256),
    description TEXT
);

INSERT INTO states (state) VALUES
    ("Завершено"),
    ("В процессе"),
    ("Отменено"),
    ("Просрочено");