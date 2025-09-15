"""
Pub/Sub → Bigtable Dataflow Pipeline
------------------------------------

Lee mensajes JSON desde una suscripción de Pub/Sub y los persiste en Bigtable.

Flags esperados:
  --project
  --region
  --subscription                (ruta completa)
  --instance_id                 (Bigtable)
  --table_id                    (Bigtable)
  --staging_location            (GCS)
  --temp_location               (GCS)
  --runner                      (DataflowRunner / DirectRunner)
  --job_name                    (opcional; se autogenera con timestamp)

Ejemplo:
  python pubsub_to_bigtable.py \
    --project=data-ecommerce-demo \
    --region=us-central1 \
    --subscription=projects/data-ecommerce-demo/subscriptions/order_events-sub-demo \
    --instance_id=bt-ecommerce \
    --table_id=product_metrics \
    --staging_location=gs://bucket-ecommerce-octavio/dataflow/staging \
    --temp_location=gs://bucket-ecommerce-octavio/dataflow/temp \
    --runner=DataflowRunner \
    --job_name=orders-to-bt-$(date +%Y%m%d-%H%M%S)
"""
import json
import time
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.bigtableio import WriteToBigTable
from google.cloud.bigtable.row import DirectRow


class ParseJson(beam.DoFn):
    def process(self, msg_bytes):
        try:
            msg = json.loads(msg_bytes.decode("utf-8"))
            # revenue = qty * unit_price
            gross_amount = round(float(msg.get("qty", 0)) * float(msg.get("unit_price", 0)), 2)

            # RowKey: product_id#event_id (ordenable por producto)
            row_key = f"{msg.get('product_id','NA')}#{msg.get('event_id','NA')}"
            row = DirectRow(row_key.encode("utf-8"))

            # Column family 'cf'
            row.set_cell("cf", b"units", str(msg.get("qty", 0)).encode("utf-8"))
            row.set_cell("cf", b"revenue", str(gross_amount).encode("utf-8"))
            row.set_cell("cf", b"event_ts", str(msg.get("event_ts","")).encode("utf-8"))
            row.set_cell("cf", b"order_id", str(msg.get("order_id","")).encode("utf-8"))
            row.set_cell("cf", b"customer_id", str(msg.get("customer_id","")).encode("utf-8"))
            row.set_cell("cf", b"currency", str(msg.get("currency","USD")).encode("utf-8"))
            yield row
        except Exception:
            # Para la demo, ignoramos mensajes inválidos sin generar warnings de Beam
            return []


def run(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--subscription", required=True)     # full path
    parser.add_argument("--instance_id", required=True)      # Bigtable
    parser.add_argument("--table_id", required=True)         # Bigtable
    parser.add_argument("--temp_location", required=True)
    parser.add_argument("--staging_location", required=True)
    parser.add_argument("--runner", default="DataflowRunner")
    parser.add_argument(
        "--job_name",
        default=f"pubsub-to-bigtable-{time.strftime('%Y%m%d-%H%M%S')}"
    )

    # parse_known_args permite pasar flags extra si hiciera falta
    args, beam_args = parser.parse_known_args(argv)

    options = PipelineOptions(
        beam_args + [
            f"--project={args.project}",
            f"--region={args.region}",
            f"--temp_location={args.temp_location}",
            f"--staging_location={args.staging_location}",
            f"--job_name={args.job_name}",
            "--save_main_session",
            "--experiments=use_runner_v2",
        ]
    )
    options.view_as(StandardOptions).runner = args.runner

    with beam.Pipeline(options=options) as p:
        (
            p
            | "ReadPubSub" >> beam.io.ReadFromPubSub(subscription=args.subscription)
            | "ParseJSON"  >> beam.ParDo(ParseJson())
            | "WriteBT"    >> WriteToBigTable(
                project_id=args.project,
                instance_id=args.instance_id,
                table_id=args.table_id
              )
        )


if __name__ == "__main__":
    run()
