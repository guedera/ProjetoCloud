import json
import os
import random
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
payments_table = dynamodb.Table(os.environ["PAYMENTS_TABLE"])
eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))

EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "payments-events")


def _log(level, message, **kwargs):
    print(json.dumps({"level": level, "message": message, **kwargs}))


def process_payment(payment_id, correlation_id):
    status = "APPROVED" if random.random() < 0.8 else "REJECTED"
    updated_at = datetime.now(timezone.utc).isoformat()

    payments_table.update_item(
        Key={"paymentId": payment_id},
        UpdateExpression="SET #s = :status, updatedAt = :updatedAt",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status, ":updatedAt": updated_at},
    )

    event_type = "PaymentApproved" if status == "APPROVED" else "PaymentRejected"
    eventbridge.put_events(
        Entries=[
            {
                "Source": "payments.worker",
                "DetailType": event_type,
                "Detail": json.dumps({"paymentId": payment_id, "status": status, "updatedAt": updated_at, "correlationId": correlation_id}),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    _log("INFO", "payment processed", paymentId=payment_id, status=status, correlationId=correlation_id)

    return status


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        payment_id = body["paymentId"]
        correlation_id = body.get("correlationId", "")
        process_payment(payment_id, correlation_id)
