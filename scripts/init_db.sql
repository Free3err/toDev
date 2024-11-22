CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    title VARCHAR(256),
    dir TEXT UNIQUE,
    state INTEGER
);

CREATE TABLE states (
    id INTEGER PRIMARY KEY,
    state VARCHAR(256)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title VARCHAR(256),
    description TEXT,
    state INTEGER
);

INSERT INTO states (state) VALUES
    ("Завершено"),
    ("В процессе"),
    ("Отменено"),
    ("Просрочено"),
    ("Не указан");

