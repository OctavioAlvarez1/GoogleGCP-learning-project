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
## 4. 📂 Pipelines

🔹 Pipeline Batch (ETL con BigQuery)

Imagen

📌 Objetivo: cargar los archivos CSV históricos desde Cloud Storage a BigQuery y generar la vista de ventas históricas (v_fact_sales_batch).

Pasos:

  1 - Subimos los archivos CSV (customers.csv, orders.csv, order_items.csv, products.csv) al bucket bucket-ecommerce-octavio/datasets/.
  2 - Desde BigQuery cargamos esos archivos a tablas dentro del dataset data_ecommerce_demo.
  3 - Creamos la vista de hechos batch:

  ```python
  CREATE OR REPLACE VIEW `data-ecommerce-demo.data_ecommerce_demo.v_fact_sales_batch` AS
  SELECT 
    o.order_id,
    TIMESTAMP(o.order_date) AS ts,  
    o.customer_id,
    oi.product_id,
    (oi.qty * oi.unit_price) AS gross_amount
  FROM `data-ecommerce-demo.data_ecommerce_demo.orders` o
  JOIN `data-ecommerce-demo.data_ecommerce_demo.order_items` oi USING (order_id);
 ```
 📌 Resultado: Vista que consolida ventas históricas con detalle de revenue por orden, cliente y producto.

 🔹 Pipeline Streaming (Pub/Sub → Dataflow → BigQuery)

 Imagen

 📌 Objetivo: procesar órdenes simuladas en tiempo real y guardarlas en BigQuery en la tabla fact_sales_streaming.

  Componentes:
  
 -  publisher.py → script que publica eventos simulados en un tópico de Pub/Sub.
 - Dataflow (Apache Beam) → pipeline que lee los eventos, los transforma y los escribe en BigQuery.
  
  Ejemplo de evento publicado
```python
  {
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "order_id": "O1234",
  "customer_id": "C054",
  "product_id": "P002",
  "qty": 2,
  "unit_price": 120.50,
  "event_ts": "2025-09-15 14:23:55"
}

```
---
## 5. 📂 Paso a Paso del Proyecto

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
  -- Cantidad de clientes por país --
  SELECT country, COUNT(*) AS total_clientes
  FROM `data-ecommerce-demo.data_ecommerce_demo.customers`
  GROUP BY country
  ORDER BY total_clientes DESC;

  -- Clientes por año de registro --
  SELECT 
    EXTRACT(YEAR FROM signup_date) AS anio_registro,
    COUNT(*) AS total_clientes
  FROM `data-ecommerce-demo.data_ecommerce_demo.customers`
  GROUP BY anio_registro
  ORDER BY anio_registro;

```
### 🔹 3. Creación de vistas para KPIs (Batch)
Ejemplo de vista de ventas históricas:

```python
  CREATE OR REPLACE VIEW `data-ecommerce-demo.data_ecommerce_demo.v_fact_sales_batch` AS
  SELECT 
    o.order_id,
    TIMESTAMP(o.order_date) AS ts,  
    o.customer_id,
    oi.product_id,
    (oi.qty * oi.unit_price) AS gross_amount
  FROM `data-ecommerce-demo.data_ecommerce_demo.orders` o
  JOIN `data-ecommerce-demo.data_ecommerce_demo.order_items` oi USING (order_id);


```
