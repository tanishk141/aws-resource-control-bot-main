import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigatewayv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";
import * as path from "path";

export class TelegramResourceControlBotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const telegramBotToken =
      this.node.tryGetContext("telegramBotToken") ||
      process.env.TELEGRAM_BOT_TOKEN ||
      "PLACEHOLDER_BOT_TOKEN";

    const allowedUserIds =
      this.node.tryGetContext("allowedUserIds") ||
      process.env.ALLOWED_USER_IDS ||
      "";

    const environmentMap =
      this.node.tryGetContext("environmentMap") ||
      JSON.parse(process.env.ENVIRONMENT_MAP || "{}");

    const webhookSecret =
      this.node.tryGetContext("webhookSecret") ||
      process.env.WEBHOOK_SECRET ||
      "";

    const botUsername =
      this.node.tryGetContext("botUsername") ||
      process.env.BOT_USERNAME ||
      "resource_control_bot";

    const accessPolicy =
      this.node.tryGetContext("accessPolicy") ||
      JSON.parse(process.env.ACCESS_POLICY || "{}");

    const auditTable = new dynamodb.Table(this, "AuditTable", {
      tableName: "TelegramResourceControlBotAudit",
      partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: "ttl",
    });

    const logGroup = new logs.LogGroup(this, "BotLogGroup", {
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const botHandler = new lambda.Function(this, "TelegramResourceControlBotHandler", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambda")),
      memorySize: 512,
      timeout: cdk.Duration.seconds(300),
      architecture: lambda.Architecture.ARM_64,
      environment: {
        TELEGRAM_BOT_TOKEN: telegramBotToken,
        ALLOWED_USER_IDS: allowedUserIds,
        ENVIRONMENT_MAP: JSON.stringify(environmentMap),
        ACCESS_POLICY: JSON.stringify(accessPolicy),
        WEBHOOK_SECRET: webhookSecret,
        AWS_REGION_NAME: cdk.Stack.of(this).region,
        AUDIT_TABLE: auditTable.tableName,
        BOT_USERNAME: botUsername,
        LOG_LEVEL: "INFO",
        DRY_RUN: "false",
      },
      logGroup: logGroup,
    });

    const httpApi = new apigatewayv2.HttpApi(this, "TelegramResourceControlBotApi", {
      apiName: "TelegramResourceControlBotApi",
      description: "HTTP API for Telegram Resource Control Bot webhook",
    });

    const lambdaIntegration = new integrations.HttpLambdaIntegration(
      "BotLambdaIntegration",
      botHandler
    );

    httpApi.addRoutes({
      path: "/telegram/webhook",
      methods: [apigatewayv2.HttpMethod.POST],
      integration: lambdaIntegration,
    });

    botHandler.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "ecs:ListServices",
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:ListClusters",
          "ecs:DescribeClusters",
        ],
        resources: ["*"],
      })
    );

    botHandler.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "rds:StartDBInstance",
          "rds:StopDBInstance",
          "rds:DescribeDBInstances",
        ],
        resources: ["*"],
      })
    );

    auditTable.grantReadWriteData(botHandler);

    botHandler.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["ssm:GetParameter"],
        resources: [
          "arn:aws:ssm:::parameter/telegram-resource-control-bot/*",
        ],
      })
    );

    new cdk.CfnOutput(this, "WebhookUrl", {
      value: `${httpApi.apiEndpoint}/telegram/webhook`,
      description: "Telegram webhook URL to register with BotFather",
    });

    new cdk.CfnOutput(this, "LambdaFunctionName", {
      value: botHandler.functionName,
      description: "Lambda function name",
    });

    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: httpApi.apiEndpoint,
      description: "API Gateway endpoint",
    });

    new cdk.CfnOutput(this, "AuditTableName", {
      value: auditTable.tableName,
      description: "DynamoDB audit trail table",
    });
  }
}
