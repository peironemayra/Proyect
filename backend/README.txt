Sistema web: Gestión integral de restaurante

Tecnologías
- Backend: FastAPI + Jinja2 + SQLAlchemy
- Base de datos: SQLite (archivo local)
- UI: HTML + CSS (sin dependencias externas)

Requisitos
- Python 3.10+

Instalación
1) Ir a la carpeta backend
2) Crear entorno virtual e instalar dependencias:
   python -m venv .venv
   .venv\Scripts\activate  (Windows)
   source .venv/bin/activate (Linux/Mac)
   pip install -r requirements.txt
3) Inicializar base de datos y usuarios:
   python scripts/init_db.py
4) Ejecutar servidor:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Acceso
- http://localhost:8000/login
- Usuarios de prueba creados por init_db.py:
  admin / Admin123*
  mozo1 / Mozo123*
  cocina1 / Cocina123*
  bar1 / Bar123*
  caja1 / Caja123*
  repartidor1 / Repartidor123*
  adminbcc / AdminBCC123*

Operación básica
- Mesas: /tables, crear pedido y agregar ítems.
- Enviar pedido: en el detalle /orders/{id}, botón "Enviar a cocina y bar".
- Cocina: /kitchen, Bar: /bar, cambiar ítems a "En preparación" y "Listo".
- Caja: /cash, abrir caja, cobrar pedidos "LISTO".
- Delivery cliente: /cliente/delivery, crear pedido y confirmar.
- Delivery admin: /delivery/admin, asignar repartidor.
- Repartidor: /delivery/my, actualizar estado.
