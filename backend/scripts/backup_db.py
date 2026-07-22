from __future__ import annotations

from app.scripts_internal import ensure_data_dirs, backup_sqlite

def main():
    ensure_data_dirs()
    path = backup_sqlite()
    if path:
        print(f"Backup creado: {path}")
    else:
        print("No se pudo crear backup (base de datos inexistente o no SQLite).")

if __name__ == "__main__":
    main()
