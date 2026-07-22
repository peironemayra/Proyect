-- Esquema base (SQLite)
-- El script crea tablas principales. El proyecto también incluye inicialización por ORM (scripts/init_db.py).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  UNIQUE(user_id, role_id),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS ix_user_roles_role_id ON user_roles(role_id);

CREATE TABLE IF NOT EXISTS session_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_session_token_token ON session_tokens(token);

CREATE TABLE IF NOT EXISTS tables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tables_code ON tables(code);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  category_id INTEGER NOT NULL,
  area TEXT NOT NULL,
  price REAL NOT NULL,
  is_available INTEGER NOT NULL DEFAULT 1,
  stock INTEGER NOT NULL DEFAULT 999999,
  prep_minutes INTEGER NOT NULL DEFAULT 10,
  created_at TEXT NOT NULL,
  FOREIGN KEY(category_id) REFERENCES categories(id)
);
CREATE INDEX IF NOT EXISTS ix_products_category_id ON products(category_id);

CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_customer_phone ON customers(phone);

CREATE TABLE IF NOT EXISTS addresses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL,
  line1 TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  table_id INTEGER,
  customer_id INTEGER,
  address_id INTEGER,
  created_by_user_id INTEGER,
  created_at TEXT NOT NULL,
  discount_pct REAL NOT NULL DEFAULT 0.0,
  notes TEXT,
  FOREIGN KEY(table_id) REFERENCES tables(id),
  FOREIGN KEY(customer_id) REFERENCES customers(id),
  FOREIGN KEY(address_id) REFERENCES addresses(id),
  FOREIGN KEY(created_by_user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_order_status ON orders(status);
CREATE INDEX IF NOT EXISTS ix_order_channel ON orders(channel);

CREATE TABLE IF NOT EXISTS order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  area TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS ix_item_status ON order_items(status);
CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL UNIQUE,
  method TEXT NOT NULL,
  amount_total REAL NOT NULL,
  amount_received REAL NOT NULL DEFAULT 0.0,
  change_due REAL NOT NULL DEFAULT 0.0,
  receipt_number TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id);

CREATE TABLE IF NOT EXISTS cash_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  opened_by_user_id INTEGER NOT NULL,
  opened_at TEXT NOT NULL,
  closed_at TEXT,
  opening_amount REAL NOT NULL DEFAULT 0.0,
  closing_amount REAL NOT NULL DEFAULT 0.0,
  is_open INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY(opened_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cash_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cash_session_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  description TEXT NOT NULL,
  amount REAL NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(cash_session_id) REFERENCES cash_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_cash_movement_time ON cash_movements(created_at);

CREATE TABLE IF NOT EXISTS deliveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL UNIQUE,
  status TEXT NOT NULL,
  assigned_to_user_id INTEGER,
  assigned_at TEXT,
  left_at TEXT,
  delivered_at TEXT,
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY(assigned_to_user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_delivery_status ON deliveries(status);
