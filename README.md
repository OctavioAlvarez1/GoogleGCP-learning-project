# 📌 Proyecto E-commerce Analytics (Batch + Streaming)

## 1. 🚀 Descripción del Proyecto
Este proyecto implementa una **arquitectura moderna de Analytics para E-commerce**, integrando datos históricos (batch) y datos en tiempo real (streaming).  

El objetivo es **crear dashboards en Looker Studio** que permitan analizar métricas clave del negocio:
- Ingresos (*Revenue*).  
- Órdenes totales y detalle por producto.  
- Clientes únicos y su distribución geográfica.  
- Ticket promedio (*Average Order Value - AOV*).  
- Comparativa entre batch (histórico) y streaming (tiempo real).  

---

## 2. 🛠️ Servicios de Google Cloud utilizados
| Servicio | Uso en el Proyecto |
|----------|--------------------|
| ![Cloud Storage](./imagenes/cloud_storage.png) | Almacenamiento de los CSV batch y los scripts Python. |
| ![BigQuery](./imagenes/bigquery.png) | Data Warehouse para datos históricos, vistas analíticas y unión batch + streaming. |
| ![Pub/Sub](./imagenes/pubsub.png) | Ingesta de eventos en tiempo real (órdenes simuladas). |
| ![Dataflow](./imagenes/dataflow.png) | Pipeline de streaming que procesa los eventos y los inserta en BigQuery. |
| ![Python](./imagenes/python.png) | Scripts de simulación (`publisher.py`) y pipeline. |
| Looker Studio | Dashboards interactivos para análisis. |

---

## 3. 🗂️ Modelo Entidad-Relación (ERD)

### Tablas principales
- **Customers**
  - `customer_id (PK)`
  - `name`
  - `country`
  - `signup_date`

- **Orders**
  - `order_id (PK)`
  - `customer_id (FK)`
  - `order_date`

- **OrderItems**
  - `order_id (FK)`
  - `product_id (FK)`
  - `qty`
  - `unit_price`

- **Products**
  - `product_id (PK)`
  - `category`
  - `price`

### Relaciones
- **Customers (1) → (N) Orders**  
- **Orders (1) → (N) OrderItems**  
- **Products (1) → (N) OrderItems**  

📌 **OrderItems es la tabla puente**: conecta órdenes con productos y permite calcular métricas como revenue.  

![Modelo ER](./imagenes/modelo_er.png)  

---

## 4. 📂 Paso a Paso del Proyecto

### 🔹 1. Ingesta en Cloud Storage
Se creó el bucket **`bucket-ecommerce-octavio`** con:
- Carpeta `/datasets` → CSV históricos (customers, orders, order_items, products).  
- Carpeta `/pipelines` → scripts Python:  
  - **publisher.py** → publica eventos simulados en Pub/Sub.  

```python
import json, time, uuid, random
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = "projects/data-ecommerce-demo/topics/order_events"

while True:
    event = {
        "event_id": str(uuid.uuid4()),
        "order_id": f"O{random.randint(1000,9999)}",
        "customer_id": f"C{random.randint(1,100)}",
        "product_id": f"P{random.randint(1,50)}",
        "qty": random.randint(1,5),
        "unit_price": round(random.uniform(10,500),2),
        "event_ts": str(time.time())
    }
    publisher.publish(topic_path, json.dumps(event).encode("utf-8"))
    print("Published:", event)
    time.sleep(2)

```
### 🔹 2. Carga de datos en BigQuery
Se creó el dataset data_ecommerce_demo dentro del proyecto data-ecommerce-demo.
Se cargaron las tablas batch desde CSV:

- customers
- orders
- order_items
- products

Ejemplo de consultas exploratorias (batch):

```python
  -- Cantidad de clientes por país
  SELECT country, COUNT(*) AS total_clientes
  FROM `data-ecommerce-demo.data_ecommerce_demo.customers`
  GROUP BY country
  ORDER BY total_clientes DESC;

  -- Clientes por año de registro
  SELECT 
    EXTRACT(YEAR FROM signup_date) AS anio_registro,
    COUNT(*) AS total_clientes
  FROM `data-ecommerce-demo.data_ecommerce_demo.customers`
  GROUP BY anio_registro
  ORDER BY anio_registro;

```
