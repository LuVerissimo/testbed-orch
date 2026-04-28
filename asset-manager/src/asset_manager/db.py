import uuid
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key, Attr


class AlreadyReservedError(Exception):
    def __init__(self, device_id: str):
        super().__init__(f"Device {device_id} is already reserved")
        self.device_id = device_id


class DeviceStore:
    def __init__(self, table):
        self.table = table

    def reserve(self, device_id: str, requester: str, ttl_seconds: int) -> dict:
        reservation_id = uuid.uuid4().hex
        now = datetime.now(tz=timezone.utc)
        expires_at = int((now + timedelta(seconds=ttl_seconds)).timestamp())
        try:
            existing = self.table.query(
                KeyConditionExpression=Key("deviceId").eq(device_id),
                FilterExpression=Attr("status").eq("RESERVED"),
            )
            if existing.get("Items"):
                raise AlreadyReservedError(device_id)

            self.table.put_item(
                Item={
                    "deviceId": device_id,
                    "reservationId": reservation_id,
                    "reserved_by": requester,
                    "reserved_at": now.isoformat(),
                    "expires_at": expires_at,
                    "status": "RESERVED",
                },
                ConditionExpression="attribute_not_exists(deviceId)",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            raise AlreadyReservedError(device_id)

        return {
            "reservation_id": reservation_id,
            "device_id": device_id,
            "reserved_by": requester,
            "reserved_at": now.isoformat(),
            "expires_at": expires_at,
        }

    def release(self, device_id: str, reservation_id: str) -> bool:
        try:
            self.table.delete_item(
                Key={
                    "deviceId": device_id,
                    "reservationId": reservation_id,
                },
                ConditionExpression="attribute_exists(deviceId)",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def get(self, device_id: str) -> dict | None:
        result = self.table.query(KeyConditionExpression=Key("deviceId").eq(device_id))

        items = result.get("Items", [])
        if not items:
            return None
        return items[0]

    def list_by_status(self, status: str | None) -> list[dict]:
        if status is None:
            result = self.table.scan()
        else:
            result = self.table.query(
                IndexName="status-reservedBy-index",
                KeyConditionExpression=Key("status").eq(status),
            )

        return result.get("Items", [])
