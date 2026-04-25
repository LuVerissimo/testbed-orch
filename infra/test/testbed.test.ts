import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { TestbedStack } from '../lib/testbed-stack';

/**
 * CDK Assertion tests — "does synth produce the CloudFormation I expect?"
 *
 * These run entirely offline (no AWS credentials needed). The CDK App is
 * synthesized into a CloudFormation template in memory, and then we assert
 * against that JSON. Think of it as unit-testing your infrastructure.
 */
describe('TestbedStack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new TestbedStack(app, 'TestStack');
    // Template.fromStack() triggers synthesis and captures the CF template
    template = Template.fromStack(stack);
  });

  test('creates a DynamoDB table with correct key schema', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      KeySchema: Match.arrayWith([
        Match.objectLike({ AttributeName: 'deviceId',      KeyType: 'HASH'  }),
        Match.objectLike({ AttributeName: 'reservationId', KeyType: 'RANGE' }),
      ]),
    });
  });

  test('uses PAY_PER_REQUEST billing', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      BillingMode: 'PAY_PER_REQUEST',
    });
  });

  test('has point-in-time recovery enabled', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      PointInTimeRecoverySpecification: {
        PointInTimeRecoveryEnabled: true,
      },
    });
  });

  test('has TTL configured on expiresAt attribute', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TimeToLiveSpecification: {
        AttributeName: 'expiresAt',
        Enabled: true,
      },
    });
  });

  test('emits CloudFormation outputs for table name and ARN', () => {
    template.hasOutput('DeviceReservationsTableName', {
      Export: { Name: 'AssetManager-DeviceReservationsTableName' },
    });
    template.hasOutput('DeviceReservationsTableArn', {
      Export: { Name: 'AssetManager-DeviceReservationsTableArn' },
    });
  });

  test('exactly one DynamoDB table in this stack', () => {
    template.resourceCountIs('AWS::DynamoDB::Table', 1);
  });
});