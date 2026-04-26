import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as rds from "aws-cdk-lib/aws-rds";

import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

// CDK Construct levels:
//   L1 (Cfn*)  — 1:1 with a CloudFormation resource. Full control, maximum verbosity.
//                Example: new CfnTable(this, 'T', { ... })
//   L2         — Curated abstraction over L1. Secure defaults, typed props, grant methods.
//                Example: new dynamodb.Table(this, 'T', { ... })
//   L3 (Patterns) — Multiple resources wired together into a reusable pattern.
//                Example: new ApplicationLoadBalancedFargateService(...)
// We use L2 throughout this stack.

/**
 * TestbedStack — owns all shared testbed infrastructure (DynamoDB, RDS, VPC)"
 *
 * Currently provisions:
 *   - DeviceReservationsTable  (DynamoDB)
 *
 * DynamoDB over PostgreSQL because Device reservation state is written
 * by many concurrent workers, theres a need for single-digit-millisecond lookups by device ID,
 * and has no relational joins.
 *
 * PostgreSQL lives in the Test Manager stack where we need ad-hoc queries over job history.
 */
export class TestbedStack extends cdk.Stack {
  /** Exposed so other stacks or integration tests can reference the table. */
  public readonly deviceReservationsTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ── DynamoDB: Device Reservations ────────────────────────────────────────
    //
    // Key design
    // ----------
    // PK  deviceId      (STRING)  — physical/virtual device
    // SK  reservationId (STRING)  — one device can have many reservation records
    //
    // Single-table queries without a GSI:
    //   "Who currently holds device-001?" → Query PK=device-001, FilterExpression status=RESERVED
    //   "Full reservation history for device-001?" → Query PK=device-001 (all SortKeys)
    //
    // GSI (status-reservedBy-index) enables:
    //   "All AVAILABLE devices?" → Query GSI PK=AVAILABLE
    //   "All devices held by user X?" → Query GSI PK=RESERVED, SK=user-x
    //
    // Billing: PAY_PER_REQUEST (on-demand).
    // on-demand so we never throttle or over-provision. Switch to PROVISIONED + auto-scaling only
    // when you have steady-state throughput data to right-size against.
    //
    // Air-gap / classified environment flag
    // RemovalPolicy.DESTROY is fine for sandbox/dev — `cdk destroy` wipes the table.
    // In a production or classified environment you MUST use
    // RemovalPolicy.RETAIN. Accidental table deletion is an irreversible data loss event.
    // Make this a required review gate before any prod deploy.

    this.deviceReservationsTable = new dynamodb.Table(
      this,
      "DeviceReservationsTable",
      {
        tableName: "device-reservations",
        partitionKey: {
          name: "deviceId",
          type: dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: "reservationId",
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,

        // TTL — the Asset Manager sets this to (now + reservation_timeout).
        // DynamoDB quietly deletes expired rows in the background so stale
        // RESERVED records do not block future allocations.
        timeToLiveAttribute: "expiresAt",

        // Point-in-time recovery gives you a 35-day continuous backup window.
        // Mandatory for any store that holds audit-trail data; in classified
        // environments it satisfies most continuity requirements.
        pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },

        // AWS_MANAGED = DynamoDB-owned KMS key, encrypted at rest, no extra cost.
        // For a classified environment you would switch to CUSTOMER_MANAGED and
        // supply your own KMS key so you control key rotation and can revoke access.
        encryption: dynamodb.TableEncryption.AWS_MANAGED,

        // TODO(prod): change to cdk.RemovalPolicy.RETAIN before any non-dev deploy
        removalPolicy: cdk.RemovalPolicy.DESTROY,
      },
    );
    this.deviceReservationsTable.addGlobalSecondaryIndex({
      indexName: "status-reservedBy-index",
      partitionKey: {
        name: "status",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "reservedBy",
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const vpc = new ec2.Vpc(this, "TestbedVpc", {
      maxAzs: 2,
      natGateways: 1,
    });

    const database = new rds.DatabaseInstance(this, "TestbedRds", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.MICRO,
      ),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      credentials: rds.Credentials.fromGeneratedSecret("testorch"),
      deletionProtection: true,
      removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
      multiAz: false,
    });

    // ── Stack outputs ─────────────────────────────────────────────────────────
    // CfnOutput writes a value into the CloudFormation stack outputs.
    // Other stacks, CI scripts, and the Makefile can read these with:
    //   aws cloudformation describe-stacks --stack-name TestbedStack
    //     --query "Stacks[0].Outputs"
    new cdk.CfnOutput(this, "DeviceReservationsTableName", {
      value: this.deviceReservationsTable.tableName,
      description: "DynamoDB table name — device reservations",
      exportName: "AssetManager-DeviceReservationsTableName",
    });

    new cdk.CfnOutput(this, "DeviceReservationsTableArn", {
      value: this.deviceReservationsTable.tableArn,
      description: "DynamoDB table ARN — for IAM policy attachment",
      exportName: "AssetManager-DeviceReservationsTableArn",
    });
  }
}
