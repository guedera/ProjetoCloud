import json
import os
import random
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
payments_table = dynamodb.Table(os.environ["PAYMENTS_TABLE"])
eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))

EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "payments-events")


def process_payment(payment_id):
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
                "Detail": json.dumps({"paymentId": payment_id, "status": status, "updatedAt": updated_at}),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    return status


def lambda_handler(event, context):
    if os.environ.get("FORCE_FAIL") == "true":
        raise RuntimeError("FORCE_FAIL enabled — simulating worker crash for DLQ testing")

    for record in event["Records"]:
        body = json.loads(record["body"])
        payment_id = body["paymentId"]
        status = process_payment(payment_id)
        print(f"payment {payment_id} -> {status}")
