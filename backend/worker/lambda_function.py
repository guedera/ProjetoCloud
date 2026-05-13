import json
import os
import random
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
payments_table = dynamodb.Table(os.environ["PAYMENTS_TABLE"])


def process_payment(payment_id):
    status = "APPROVED" if random.random() < 0.8 else "REJECTED"
    updated_at = datetime.now(timezone.utc).isoformat()

    payments_table.update_item(
        Key={"paymentId": payment_id},
        UpdateExpression="SET #s = :status, updatedAt = :updatedAt",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status, ":updatedAt": updated_at},
    )

    return status


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        payment_id = body["paymentId"]
        status = process_payment(payment_id)
        print(f"payment {payment_id} -> {status}")
