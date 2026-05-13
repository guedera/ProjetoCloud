import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
users_table = dynamodb.Table(os.environ["USERS_TABLE"])


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


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")

    if method == "POST" and path == "/users":
        return create_user(event, context)

    if method == "GET" and path.startswith("/users/"):
        return get_user(event, context)

    return _response(404, {"error": "not_found", "message": "route not found"})
