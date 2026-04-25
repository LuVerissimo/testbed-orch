#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AssetManagerStack } from '../lib/asset-manager-stack';

const app = new cdk.App();

new AssetManagerStack(app, 'AssetManagerStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? 'us-east-1',
  },
  description: 'Asset Manager — device reservation service (DynamoDB + gRPC)',
});