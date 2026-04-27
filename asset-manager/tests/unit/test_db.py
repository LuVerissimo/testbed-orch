import boto3, pytest
from moto import mock_aws
from asset_manager.db import DeviceStore


@pytest.fixture
def store():
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="test-reservations",
            AttributeDefinitions=[
                {"AttributeName": "deviceId", "AttributeType": "S"},
                {"AttributeName": "reservationId", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
                {"AttributeName": "reservedBy", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "deviceId", "KeyType": "HASH"},
                {"AttributeName": "reservationId", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "status-reservedBy-index",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "reservedBy", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        table = boto3.resource("dynamodb", region_name="us-east-1").Table(
            "test-reservations"
        )
        yield DeviceStore(table)


def test_reserve_and_get(store):
    reservation = store.reserve("device1", "user1", ttl_seconds=3600)
    assert reservation["device_id"] == "device1"
    assert reservation["reservedBy"] == "user1"

    retrieved = store.get("device1")
    assert retrieved is not None
    assert retrieved["deviceId"] == "device1"
    assert retrieved["reservedBy"] == "user1"


def test_reserve_already_reserved(store):
    store.reserve("device1", "user1", ttl_seconds=3600)
    with pytest.raises(Exception) as exc_info:
        store.reserve("device1", "user2", ttl_seconds=3600)
    assert "already reserved" in str(exc_info.value)


def test_release(store):
    reservation = store.reserve("device1", "user1", ttl_seconds=3600)
    reservation_id = reservation["reservation_id"]

    # Release the reservation
    released = store.release("device1", reservation_id)
    assert released

    # Attempt to get the released reservation
    retrieved = store.get("device1")
    assert retrieved is None


def test_list_by_status(store):
    store.reserve("device1", "user1", ttl_seconds=3600)
    store.reserve("device2", "user2", ttl_seconds=3600)

    reserved_devices = store.list_by_status("RESERVED")
    assert len(reserved_devices) == 2
    assert all(d["status"] == "RESERVED" for d in reserved_devices)

    all_devices = store.list_by_status(None)
    assert len(all_devices) == 2


def test_release_nonexistent(store):
    released = store.release("nonexistent-device", "fake-reservation-id")
    assert not released


def test_get_nonexistent(store):
    retrieved = store.get("nonexistent-device")
    assert retrieved is None


def test_list_by_status_none(store):
    store.reserve("device1", "user1", ttl_seconds=3600)
    store.reserve("device2", "user2", ttl_seconds=3600)

    all_devices = store.list_by_status(None)
    assert len(all_devices) == 2


def test_list_by_status_no_matches(store):
    store.reserve("device1", "user1", ttl_seconds=3600)
    store.reserve("device2", "user2", ttl_seconds=3600)

    available_devices = store.list_by_status("AVAILABLE")
    assert len(available_devices) == 0


def test_reserve_and_get_multiple(store):
    reservation1 = store.reserve("device1", "user1", ttl_seconds=3600)
    reservation2 = store.reserve("device2", "user2", ttl_seconds=3600)

    retrieved1 = store.get("device1")
    retrieved2 = store.get("device2")

    assert retrieved1 is not None
    assert retrieved1["deviceId"] == "device1"
    assert retrieved1["reservedBy"] == "user1"

    assert retrieved2 is not None
    assert retrieved2["deviceId"] == "device2"
    assert retrieved2["reservedBy"] == "user2"


def test_reserve_and_release_multiple(store):
    reservation1 = store.reserve("device1", "user1", ttl_seconds=3600)
    reservation2 = store.reserve("device2", "user2", ttl_seconds=3600)

    reservation_id1 = reservation1["reservation_id"]
    reservation_id2 = reservation2["reservation_id"]

    # Release the reservations
    released1 = store.release("device1", reservation_id1)
    released2 = store.release("device2", reservation_id2)

    assert released1
    assert released2

    # Attempt to get the released reservations
    retrieved1 = store.get("device1")
    retrieved2 = store.get("device2")

    assert retrieved1 is None
    assert retrieved2 is None
