from __future__ import annotations

from datetime import datetime
import random
import string

def new_order_code() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=6))
    return f"ORD-{stamp}-{suffix}"

def new_receipt_number() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"RC-{stamp}-{suffix}"

def new_table_code(n: int) -> str:
    return f"M{n:02d}"
