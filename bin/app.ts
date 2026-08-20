import * as cdk from "aws-cdk-lib";
import { TelegramResourceControlBotStack } from "../lib/telegram-resource-control-bot-stack";

const app = new cdk.App();

new TelegramResourceControlBotStack(app, "TelegramResourceControlBotStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || "us-east-1",
  },
});
