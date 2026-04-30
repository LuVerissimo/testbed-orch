import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export class TestManagerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const failed = new cloudwatch.Metric({
      namespace: "TestOrch/Worker",
      metricName: "JOBS_FAILED",
      statistic: "Sum",
      period: cdk.Duration.minutes(5),
    });

    const submitted = new cloudwatch.Metric({
      namespace: "TestOrch/Worker",
      metricName: "JOBS_SUBMITTED",
      statistic: "Sum",
      period: cdk.Duration.minutes(5),
    });

    const failureRate = new cloudwatch.MathExpression({
      expression: "(failed / submitted) * 100",
      usingMetrics: { failed, submitted },
    });

    new cloudwatch.Alarm(this, "HighFailureRate", {
      metric: failureRate,
      threshold: 10,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
  }
}
