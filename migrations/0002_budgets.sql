CREATE TABLE budgets (
    category      TEXT    PRIMARY KEY,                          -- đã chuẩn hóa (normalize_category)
    monthly_limit INTEGER NOT NULL CHECK (monthly_limit > 0)    -- đơn vị: đồng
);
