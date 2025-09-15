"""
Publisher de eventos de ventas a Pub/Sub
----------------------------------------

Este script simula un flujo de datos de un e-commerce, generando órdenes de compra
aleatorias y publicándolas en un tópico de Pub/Sub.

Características:
- Genera 100 mensajes de prueba (1 por segundo).
- Cada evento incluye: event_id, order_id, customer_id, product_id, qty, unit_price,
  currency y timestamp.
- Publica en el tópico Pub/Sub: projects/data-ecommerce-demo/topics/order_events
- Útil para probar pipelines de streaming (ej. Dataflow → Bigtable → BigQuery/Looker).

Uso:
    python3 publisher.py
"""

import json, time, uuid, random, datetime
from google.cloud import pubsub_v1

# Configuración
PROJECT_ID = "data-ecommerce-demo"   # Project ID
TOPIC_ID = "order_events"            # nombre del tema

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

# Datos de prueba
products = ["P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"]
customers = [f"C{i:03d}" for i in range(1, 101)]

# Genero datos en formato json por cada segundo
for _ in range(100):  # va a generar 100 mensajes
    qty = random.randint(1, 5)
    unit_price = round(random.uniform(5, 200), 2)

    msg = {
        "event_id": str(uuid.uuid4()),
        "order_id": str(uuid.uuid4()),
        "customer_id": random.choice(customers),
        "product_id": random.choice(products),
        "qty": qty,
        "unit_price": unit_price,
        "gross_amount": round(qty * unit_price, 2),  # 👈 agregado
        "currency": "USD",
        "event_ts": datetime.datetime.utcnow().isoformat() + "Z"
    }

    future = publisher.publish(topic_path, json.dumps(msg).encode("utf-8"))
    print("Published:", msg)

    time.sleep(1)  # 1 mensaje por segundo
