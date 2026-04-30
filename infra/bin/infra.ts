#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { TestbedStack } from "../lib/testbed-stack";
import { TestManagerStack } from "../lib/test-manager-stack";

const app = new cdk.App();

new TestbedStack(app, "TestbedStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
  description: "Asset Manager — device reservation service (DynamoDB + gRPC)",
});

new TestManagerStack(app, "TestManagerStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
  description: "Test Manager — device reservation service (DynamoDB + gRPC)",
});
