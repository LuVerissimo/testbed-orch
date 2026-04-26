import grpc, os, boto3, uuid
from .generated import asset_manager_pb2, asset_manager_pb2_grpc
from datetime import datetime, timedelta


class AssetManagerService(asset_manager_pb2_grpc.AssetManagerServicer):
    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb", endpoint_url=os.environ("DYNAMODB_ENDPOINT_URL")
        )
        self.TABLE_NAME = os.environ("DYNAMODB_TABLE_NAME")
        self.table = self.dynamodb.Table(self.TABLE_NAME)

    def ReserveDevice(self, request, context):
        reservation_id = uuid.uuid4().hex
        expires_at_dt = datetime.now() + timedelta(seconds=request.duration_seconds)
        expires_at = expires_at_dt.isoformat()

        try:
            self.table.put_item(
                Item={
                    "reservation_id": reservation_id,
                    "device_id": request.device_id,
                    "reserved_by": request.reserved_by,
                    "reserved_at": str(datetime.now()),
                    "expires_at": expires_at,
                },
                ConditionExpression="attribute_not_exists(device_id)",
            )

            reservation = asset_manager_pb2.Reservation(
                reservation_id=reservation_id,
                device_id=request.device_id,
                reserved_by=request.reserved_by,
            )

            return asset_manager_pb2.ReserveDeviceResponse(reservation=reservation)

        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Device is already reserved")
            return asset_manager_pb2.ReserveDeviceResponse()

    def ReleaseDevice(self, request, context):
        try:
            self.table.delete_item(Key={"reservation_id": request.reservation_id})
            return asset_manager_pb2.ReleaseDeviceResponse(success=True)
        except Exception as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Reservation not found")
            return asset_manager_pb2.ReleaseDeviceResponse(success=False)

    # def GetDevice(self, request, context):
    # def ListDevices(self, request, context):

    # def serve():
    #     server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    #     asset_manager_pb2_grpc.add_DeviceServiceServicer_to_server(
    #         YourServicer(), server
    #     )
    #     server.add_insecure_port("[::]:50051")
    #     server.start()
    #     server.wait_for_termination()
