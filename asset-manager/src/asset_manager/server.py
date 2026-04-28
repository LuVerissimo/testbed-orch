from grpc_reflection.v1alpha import reflection
import grpc, os, boto3, logging
from .generated import asset_manager_pb2, asset_manager_pb2_grpc
from concurrent import futures
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from .db import DeviceStore, AlreadyReservedError


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
        self.store = DeviceStore(self.table)

    def ReserveDevice(self, request, context):
        try:
            r = self.store.reserve(
                request.device_id, request.reserved_by, request.duration_seconds
            )
        except AlreadyReservedError:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Device is already reserved")
            return asset_manager_pb2.ReserveDeviceResponse()

        reservation = asset_manager_pb2.Reservation(
            reservation_id=r["reservation_id"],
            device_id=r["device_id"],
            reserved_by=r["reserved_by"],
            reserved_at=_to_proto_ts(datetime.fromisoformat(r["reserved_at"])),
            expires_at=_to_proto_ts(
                datetime.fromtimestamp(r["expires_at"], tz=timezone.utc)
            ),
        )
        return asset_manager_pb2.ReserveDeviceResponse(reservation=reservation)

    def ReleaseDevice(self, request, context):
        released = self.store.release(request.device_id, request.reservation_id)
        if not released:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Reservation not found")
            return asset_manager_pb2.ReleaseDeviceResponse(success=False)
        return asset_manager_pb2.ReleaseDeviceResponse(success=True)

    def GetDevice(self, request, context):
        item = self.store.get(request.device_id)
        if item is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return asset_manager_pb2.GetDeviceResponse()

        device = asset_manager_pb2.Device(
            device_id=item["deviceId"],
            device_hostname=item.get("device_hostname", ""),
            status=_STR_TO_STATUS.get(item.get("status", "UNSPECIFIED"), 0),
            device_label=item.get("device_label", ""),
        )
        return asset_manager_pb2.GetDeviceResponse(device=device)

    def ListDevices(self, request, context):
        status = request.status

        if status == asset_manager_pb2.DEVICE_STATUS_UNSPECIFIED:
            result = self.store.list_by_status(None)
        else:
            status_str = _STATUS_TO_STR.get(status, "UNSPECIFIED")
            result = self.store.list_by_status(status_str)

        devices = [
            asset_manager_pb2.Device(
                device_id=item["deviceId"],
                device_hostname=item.get("device_hostname", ""),
                status=_STR_TO_STATUS.get(item.get("status", "UNSPECIFIED"), 0),
                device_label=item.get("device_label", ""),
            )
            for item in result
        ]
        return asset_manager_pb2.ListDevicesResponse(devices=devices)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def serve():
    port = os.environ.get("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    asset_manager_pb2_grpc.add_DeviceServiceServicer_to_server(
        DeviceServiceServicer(), server
    )
    service_names = (
        asset_manager_pb2.DESCRIPTOR.services_by_name["DeviceService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)
    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    logger.info("Asset Manager gRPC server listening on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
