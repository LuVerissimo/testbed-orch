import grpc, uuid, pytest
from asset_manager.generated import asset_manager_pb2, asset_manager_pb2_grpc


@pytest.fixture(scope="module")
def grpc_stub():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = asset_manager_pb2_grpc.DeviceServiceStub(channel)
        yield stub


def test_reserve_device(grpc_stub):
    device_id = uuid.uuid4().hex
    reservation = grpc_stub.ReserveDevice(
        asset_manager_pb2.ReserveDeviceRequest(
            device_id=device_id, reserved_by="test_user", duration_seconds=60
        )
    )
    assert reservation.reservation.device_id == device_id
    assert reservation.reservation.reserved_by == "test_user"

    retrieved = grpc_stub.GetDevice(
        asset_manager_pb2.GetDeviceRequest(device_id=device_id)
    )
    assert retrieved.device.device_id == device_id


def test_device_unavailable(grpc_stub):
    device_id = uuid.uuid4().hex
    grpc_stub.ReserveDevice(
        asset_manager_pb2.ReserveDeviceRequest(
            device_id=device_id, reserved_by="test_user_1", duration_seconds=60
        )
    )
    with pytest.raises(grpc.RpcError) as exc_info:
        grpc_stub.ReserveDevice(
            asset_manager_pb2.ReserveDeviceRequest(
                device_id=device_id, reserved_by="test_user_2", duration_seconds=60
            )
        )
    assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS


def test_release_device(grpc_stub):
    device_id = uuid.uuid4().hex
    reservation = grpc_stub.ReserveDevice(
        asset_manager_pb2.ReserveDeviceRequest(
            device_id=device_id, reserved_by="test_user", duration_seconds=60
        )
    )
    released = grpc_stub.ReleaseDevice(
        asset_manager_pb2.ReleaseDeviceRequest(
            device_id=device_id,
            reservation_id=reservation.reservation.reservation_id,
        )
    )
    assert released.success
    with pytest.raises(grpc.RpcError) as exc:
        grpc_stub.GetDevice(asset_manager_pb2.GetDeviceRequest(device_id=device_id))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND


def test_release_and_rereserve(grpc_stub):
    device_id = uuid.uuid4().hex
    r = grpc_stub.ReserveDevice(
        asset_manager_pb2.ReserveDeviceRequest(
            device_id=device_id, reserved_by="test_user", duration_seconds=60
        )
    )
    grpc_stub.ReleaseDevice(
        asset_manager_pb2.ReleaseDeviceRequest(
            device_id=device_id,
            reservation_id=r.reservation.reservation_id,
        )
    )
    r2 = grpc_stub.ReserveDevice(
        asset_manager_pb2.ReserveDeviceRequest(
            device_id=device_id, reserved_by="test_user", duration_seconds=60
        )
    )
    assert r2.reservation.reservation_id != r.reservation.reservation_id
