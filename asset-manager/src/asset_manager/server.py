import grpc, os, boto3, uuid
from .generated import asset_manager_pb2, asset_manager_pb2_grpc
from boto3.dynamodb.conditions import Key
from concurrent import futures
from datetime import datetime, timedelta, timezone
from google.protobuf.timestamp_pb2 import Timestamp


_STATUS_TO_STR = {
    asset_manager_pb2.DEVICE_STATUS_UNSPECIFIED: "UNSPECIFIED",
    asset_manager_pb2.DEVICE_STATUS_AVAILABLE: "AVAILABLE",
    asset_manager_pb2.DEVICE_STATUS_RESERVED: "RESERVED",
    asset_manager_pb2.DEVICE_STATUS_OFFLINE: "OFFLINE",
}
_STR_TO_STATUS = {v: k for k, v in _STATUS_TO_STR.items()}


def _to_proto_ts(dt: datetime) -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(dt.astimezone(timezone.utc))
    return ts


class DeviceServiceServicer(asset_manager_pb2_grpc.DeviceServiceServicer):
    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb", endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL")
        )
        self.table = self.dynamodb.Table(os.environ.get("DYNAMODB_TABLE_NAME"))

    def ReserveDevice(self, request, context):
        reservation_id = uuid.uuid4().hex
        now = datetime.now(tz=timezone.utc)
        expires_at_dt = now + timedelta(seconds=request.duration_seconds)

        try:
            self.table.put_item(
                Item={
                    "deviceId": request.device_id,
                    "reservationId": reservation_id,
                    "reserved_by": request.reserved_by,
                    "reserved_at": str(datetime.now()),
                    "expiresAt": int(expires_at_dt.timestamp()),
                    "status": "RESERVED",
                },
                ConditionExpression="attribute_not_exists(deviceId)",
            )
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Device is already reserved")
            return asset_manager_pb2.ReserveDeviceResponse()

        reservation = asset_manager_pb2.Reservation(
            reservation_id=reservation_id,
            device_id=request.device_id,
            reserved_by=request.reserved_by,
            reserved_at=_to_proto_ts(now),
            expires_at=_to_proto_ts(expires_at_dt),
        )

        return asset_manager_pb2.ReserveDeviceResponse(reservation=reservation)

    def ReleaseDevice(self, request, context):
        try:
            self.table.delete_item(
                Key={
                    "deviceId": request.device_id,
                    "reservationId": request.reservation_id,
                },
                ConditionExpression="attribute_exists(deviceId)",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Reservation not found")
            return asset_manager_pb2.ReleaseDeviceResponse(success=False)

        return asset_manager_pb2.ReleaseDeviceResponse(success=True)

    def GetDevice(self, request, context):
        result = self.table.query(
            KeyConditionExpression=Key("deviceId").eq(request.device_id)
        )
        items = result.get("Items", [])

        if not items:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Device not found")
            return asset_manager_pb2.GetDeviceResponse()

        item = items[0]
        device = asset_manager_pb2.Device(
            device_id=item["deviceId"],
            device_hostname=item.get("device_hostname", ""),
            status=_STR_TO_STATUS.get(item.get("status", "UNSPECIFIED"), 0),
            device_label=item.get("device_label", ""),
        )
        return asset_manager_pb2.GetDeviceResponse(device=device)

    def ListDevices(self, request, context):
        if request.status == asset_manager_pb2.DEVICE_STATUS_UNSPECIFIED:
            result = self.table.scan()
        else:
            status_str = _STATUS_TO_STR.get(request.status, "UNSPECIFIED")
            result = self.table.query(
                IndexName="status-reservedBy-index",
                KeyConditionExpression=Key("status").eq(status_str),
            )

        devices = [
            asset_manager_pb2.Device(
                device_id=item["deviceId"],
                device_hostname=item.get("device_hostname", ""),
                status=_STR_TO_STATUS.get(item.get("status", "UNSPECIFIED"), 0),
                device_label=item.get("device_label", ""),
            )
            for item in result.get("Items", [])
        ]
        return asset_manager_pb2.ListDevicesResponse(devices=devices)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    asset_manager_pb2_grpc.add_DeviceServiceServicer_to_server(
        asset_manager_pb2_grpc.DeviceServiceServicer(), server
    )
    # server.add_insecure_port("[::]:50051")
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
