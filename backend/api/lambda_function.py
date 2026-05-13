import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))

users_table = dynamodb.Table(os.environ["USERS_TABLE"])
payments_table = dynamodb.Table(os.environ["PAYMENTS_TABLE"])
payments_queue_url = os.environ["PAYMENTS_QUEUE_URL"]


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def create_user(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "invalid_json", "message": "request body is not valid JSON"})

    name = body.get("name", "").strip()
    email = body.get("email", "").strip()

    if not name:
        return _response(400, {"error": "missing_field", "message": "name is required"})
    if not email:
        return _response(400, {"error": "missing_field", "message": "email is required"})

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "userId": user_id,
        "name": name,
        "email": email,
        "createdAt": created_at,
    }

    try:
        users_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(email)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(409, {"error": "conflict", "message": "email already exists"})

    return _response(201, item)


def get_user(event, context):
    user_id = (event.get("pathParameters") or {}).get("id")

    if not user_id:
        return _response(400, {"error": "missing_param", "message": "id is required"})

    result = users_table.get_item(Key={"userId": user_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": "not_found", "message": "user not found"})

    return _response(200, item)


def create_payment(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "invalid_json", "message": "request body is not valid JSON"})

    user_id = body.get("userId", "").strip()
    amount = body.get("amount")
    currency = body.get("currency", "").strip()
    description = body.get("description", "").strip()
    idempotency_key = (event.get("headers") or {}).get("Idempotency-Key", "").strip()

    if not user_id:
        return _response(400, {"error": "missing_field", "message": "userId is required"})
    if amount is None:
        return _response(400, {"error": "missing_field", "message": "amount is required"})
    if not currency:
        return _response(400, {"error": "missing_field", "message": "currency is required"})

    user_result = users_table.get_item(Key={"userId": user_id})
    if not user_result.get("Item"):
        return _response(404, {"error": "not_found", "message": "user not found"})

    if idempotency_key:
        existing = payments_table.query(
            IndexName="idempotencyKey-index",
            KeyConditionExpression=Key("idempotencyKey").eq(idempotency_key),
        )
        if existing.get("Items"):
            return _response(409, existing["Items"][0])

    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "paymentId": payment_id,
        "userId": user_id,
        "amount": str(amount),
        "currency": currency,
        "description": description,
        "status": "PENDING",
        "createdAt": created_at,
    }
    if idempotency_key:
        item["idempotencyKey"] = idempotency_key

    payments_table.put_item(Item=item)

    sqs.send_message(
        QueueUrl=payments_queue_url,
        MessageBody=json.dumps({"paymentId": payment_id}),
    )

    return _response(202, item)


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")

    if method == "POST" and path == "/users":
        return create_user(event, context)

    if method == "GET" and path.startswith("/users/"):
        return get_user(event, context)

    if method == "POST" and path == "/payments":
        return create_payment(event, context)

    return _response(404, {"error": "not_found", "message": "route not found"})
