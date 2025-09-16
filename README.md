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
|  <div align="center"><img src="Imagenes/bigquery.png" width="50" height="50"/></div>  | **BigQuery**: Data Warehouse para datos históricos, vistas analíticas y unión batch + streaming. |
| <div align="center"><img src="Imagenes/pub.png" width="50" height="50"/></div> | **Pub/Sub**: Ingesta de eventos en tiempo real (órdenes simuladas). |
| <div align="center"><img src="Imagenes/dataflow.png" width="50" height="50"/></div>  | **DataFlow**: Pipeline de streaming que procesa los eventos y los inserta en BigQuery. |
| <div align="center"><img src="Imagenes/python.png" width="50" height="50"/></div> | **Python**: Scripts de simulación (`publisher.py`) y pipeline. |
| <div align="center"><img src="Imagenes/looker.png" width="50" height="50"/></div> | **Looker Studio**: Dashboards interactivos para análisis. |

---

## 3. 🗂️ Modelo Entidad-Relación (ERD)

<div align="center"><img src="Imagenes/MER.png" width="600" /></div>

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



---
## 4. 📂 Pipelines

🔹 Pipeline Batch (ETL con BigQuery)

<div align="center"><img src="Imagenes/batch.png" width="2419" height="798"/></div>

📌 Objetivo: cargar los archivos CSV históricos desde Cloud Storage a BigQuery y generar la vista de ventas históricas (v_fact_sales_batch).

Pasos:
  1 - Creo el bucket ecommerce-demo-bucket en Cloud Storage con las carpetas datasets y pipelines
  2 - Subo los archivos CSV (customers.csv, orders.csv, order_items.csv, products.csv) al bucket ecommerce-demo-bucker/datasets/.
  <br>
  2 - Desde BigQuery cargo esos archivos a tablas dentro del dataset data_ecommerce_demo.
  <br>
  4 - Creamos la vista de hechos batch:

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
 
---
 🔹 Pipeline Streaming (Pub/Sub → Dataflow → BigQuery)

 <div align="center"><img src="Imagenes/Streaming.png"/></div>

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
Vista que unifica batch y streaming
```python

-- Vista que combina batch con streaming para ser utilizada en Looker Studio --

CREATE OR REPLACE VIEW `data-ecommerce-demo.data_ecommerce_demo.v_fact_sales_all` AS
-- Histórico (batch)
SELECT 
  o.order_id,
  TIMESTAMP(o.order_date) AS ts,  
  o.customer_id,
  oi.product_id,
  (oi.qty * oi.unit_price) AS gross_amount,
  'batch' AS source
FROM `data-ecommerce-demo.data_ecommerce_demo.orders` o
JOIN `data-ecommerce-demo.data_ecommerce_demo.order_items` oi USING (order_id)

UNION ALL

-- Streaming (tiempo real)
SELECT 
  order_id,
  event_ts AS ts,
  customer_id,
  product_id,
  gross_amount,
  'streaming' AS source
FROM `data-ecommerce-demo.data_ecommerce_demo.fact_sales_streaming`;

```
📌 Resultado: cada orden publicada en Pub/Sub aparece en tiempo real en BigQuery → tabla

---

### 🔹 4. Dashboard Batch

<div align="center"><img src="Imagenes/batchDashboard.png"/></div>

**KPIs principales:**

  - Total Revenue
  - Total Orders
  - Unique Clients
  - Average Order Value (AOV)

**Gráficos:**

  - Revenue a lo largo del tiempo → crecimiento acumulado.
  - Revenue por categoría → distribución entre Books, Clothing, Electronics, etc.
  - Revenue por cliente/país/categoría → tabla de detalle.
  - Revenue por país → mapa geográfico.

📌 Insights:

  - Chile y Argentina concentran la mayoría de clientes.
  - Electronics y Books son las categorías más rentables.
  - Ticket promedio (AOV): $1.465,68.

### 🔹 4. Dashboard Streaming
