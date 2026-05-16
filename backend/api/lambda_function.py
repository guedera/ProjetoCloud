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


def _log(level, message, **kwargs):
    print(json.dumps({"level": level, "message": message, **kwargs}))


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
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    idempotency_key = headers.get("idempotency-key", "").strip()

    if not user_id:
        return _response(400, {"error": "missing_field", "message": "userId is required"})
    if amount is None:
        return _response(400, {"error": "missing_field", "message": "amount is required"})
    if not currency:
        return _response(400, {"error": "missing_field", "message": "currency is required"})

    user_result = users_table.get_item(Key={"userId": user_id})
    if not user_result.get("Item"):
        return _response(404, {"error": "not_found", "message": "user not found"})

    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    if idempotency_key:
        # Use idempotency_key as a deterministic paymentId prefix so the same
        # key always maps to the same item — collision is caught atomically by DynamoDB.
        payment_id = f"pay_{idempotency_key[:16]}"

    correlation_id = str(uuid.uuid4())
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

    try:
        payments_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(paymentId)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        existing = payments_table.get_item(Key={"paymentId": payment_id})
        return _response(409, existing.get("Item", {}))

    sqs.send_message(
        QueueUrl=payments_queue_url,
        MessageBody=json.dumps({"paymentId": payment_id, "correlationId": correlation_id}),
    )

    _log("INFO", "payment created", paymentId=payment_id, userId=user_id, correlationId=correlation_id)

    return _response(202, item)


def list_payments(event, context):
    user_id = (event.get("queryStringParameters") or {}).get("userId")

    if not user_id:
        return _response(400, {"error": "missing_param", "message": "userId query param is required"})

    result = payments_table.query(
        IndexName="userId-index",
        KeyConditionExpression=Key("userId").eq(user_id),
    )

    return _response(200, {"items": result.get("Items", []), "count": result.get("Count", 0)})


def get_payment(event, context):
    payment_id = (event.get("pathParameters") or {}).get("id")

    if not payment_id:
        return _response(400, {"error": "missing_param", "message": "id is required"})

    result = payments_table.get_item(Key={"paymentId": payment_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": "not_found", "message": "payment not found"})

    return _response(200, item)


def list_users(event, context):
    result = users_table.scan()
    items = sorted(result.get("Items", []), key=lambda u: u.get("createdAt", ""))
    return _response(200, {"items": items, "count": len(items)})


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")

    if method == "POST" and path == "/users":
        return create_user(event, context)

    if method == "GET" and path == "/users":
        return list_users(event, context)

    if method == "GET" and path.startswith("/users/"):
        return get_user(event, context)

    if method == "POST" and path == "/payments":
        return create_payment(event, context)

    if method == "GET" and path == "/payments":
        return list_payments(event, context)

    if method == "GET" and path.startswith("/payments/"):
        return get_payment(event, context)

    return _response(404, {"error": "not_found", "message": "route not found"})
