CREATE TABLE expenses (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    amount    INTEGER NOT NULL CHECK (amount > 0), -- đơn vị: đồng
    category  TEXT    NOT NULL,
    note      TEXT    NOT NULL DEFAULT '',
    spent_on  TEXT    NOT NULL                     -- ISO date YYYY-MM-DD
);
