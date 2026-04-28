# Start just LocalStack

docker compose up localstack

# In a separate terminal, check the table was auto-created

python3 - <<'EOF'
import boto3
client = boto3.client("dynamodb", endpoint_url="http://localhost:4566",
region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
print(client.describe_table(TableName="device-reservations")["Table"]["TableStatus"])
EOF

# Start the server

make run-asset-manager

<!-- you should see cd asset-manager && python3 -m asset_manager.server
INFO Found credentials in environment variables.
2026-04-26 14:15:05,730 INFO Asset Manager gRPC server listening on port 50051 -->

# From another terminal

grpcurl -plaintext \
 -import-path proto -proto asset_manager.proto \
 -d '{"device_id":"device-001","reserved_by":"me","duration_seconds":60}' \
 localhost:50051 asset_manager.DeviceService/ReserveDevice

<!-- the return should be something like this: -->

{
"reservation": {
"reservationId": "7185961b13b446b5b74cf2de024e02ee",
"deviceId": "device-001",
"reserved_by": "me",
"reserved_at": "2026-04-26T18:16:55.045725Z",
"expires_at": "2026-04-26T18:17:55.045725Z"
}
}
