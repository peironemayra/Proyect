-- Seed mínimo (SQLite)
PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO roles(code, name) VALUES
('ADMIN_GENERAL', 'Administrador General'),
('ADMIN_BCC', 'Administrador BCC'),
('MOZO', 'Mozo'),
('COCINA', 'Cocina'),
('BAR', 'Bar'),
('CAJA', 'Caja'),
('REPARTIDOR', 'Repartidor');

INSERT OR IGNORE INTO categories(name, created_at) VALUES
('Entradas', datetime('now')),
('Platos fuertes', datetime('now')),
('Bebidas', datetime('now')),
('Postres', datetime('now'));
