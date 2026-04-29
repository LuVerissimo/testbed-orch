docker compose build asset-manager
docker compose up -d asset-manager

Reserve Device

```
grpcurl -plaintext \
 -d '{"device_id": "device-001", "reserved_by": "me", "duration_seconds": 60}' \
 localhost:50051 \
 asset_manager.DeviceService/ReserveDevice
```

response should look like:

```
    "reservation": {
        "reservation_id": "26db7f4d810d4c9a93cae2c0b1af600b",
        "device_id": "device-005",
        "reserved_by": "me",
        "reserved_at": "2026-04-28T21:29:51.678641Z",
        "expires_at": "2026-04-28T21:30:51Z"
    }
```

Release Device

```
grpcurl -plaintext \
 -d '{"reservation_id": "26db7f4d810d4c9a93cae2c0b1af600b"}' \
 localhost:50051 \
 asset_manager.DeviceService/ReleaseDevice
```
