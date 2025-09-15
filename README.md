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
|  <div align="center"><img src="Imagenes/cloudstorage.png" width="50" height="50"/></div> | **Cloud Storage**: almacenamiento de los CSV batch y los scripts Python. |
| ![BigQuery](./imagenes/bigquery.png) | **BigQuery**: Data Warehouse para datos históricos, vistas analíticas y unión batch + streaming. |
| ![Pub/Sub](./imagenes/pubsub.png) | **Pub/Sub**: Ingesta de eventos en tiempo real (órdenes simuladas). |
| ![Dataflow](./imagenes/dataflow.png) | **DataFlow**: Pipeline de streaming que procesa los eventos y los inserta en BigQuery. |
| ![Python](./imagenes/python.png) | **Python**: Scripts de simulación (`publisher.py`) y pipeline. |
| Looker Studio | **Looker Studio**: Dashboards interactivos para análisis. |

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
  
 - Archivo publisher.py → script en Python que publica eventos simulados en un Tema de Pub/Sub.
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
Código principal del pipeline (simplificado - publisher.py )
```python

import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery

class ParseJson(beam.DoFn):
    def process(self, msg_bytes):
        msg = json.loads(msg_bytes.decode("utf-8"))
        yield {
            "order_id": msg.get("order_id"),
            "customer_id": msg.get("customer_id"),
            "product_id": msg.get("product_id"),
            "gross_amount": float(msg.get("qty",0)) * float(msg.get("unit_price",0)),
            "event_ts": msg.get("event_ts")
        }

def run():
    options = PipelineOptions(
        runner="DataflowRunner",
        project="data-ecommerce-demo",
        region="us-central1",
        temp_location="gs://bucket-ecommerce-octavio/temp",
        staging_location="gs://bucket-ecommerce-octavio/staging",
        job_name="pubsub-to-bigquery-demo"
    )
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        (p
         | "ReadPubSub" >> beam.io.ReadFromPubSub(
                subscription="projects/data-ecommerce-demo/subscriptions/order_events-sub-demo")
         | "ParseJSON" >> beam.ParDo(ParseJson())
         | "WriteToBQ" >> WriteToBigQuery(
                table="data-ecommerce-demo.data_ecommerce_demo.fact_sales_streaming",
                schema="order_id:STRING, customer_id:STRING, product_id:STRING, gross_amount:FLOAT, event_ts:TIMESTAMP",
                write_disposition="WRITE_APPEND"
            )
        )

```
📌 Resultado: cada orden publicada en Pub/Sub aparece en tiempo real en BigQuery → tabla

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
