# 📦 Setup Project from GitHub

After cloning from GitHub, follow these steps to get the project running locally.

## Prerequisites

- Node.js 14+ installed
- Python 3.12 installed
- AWS credentials configured (`aws configure`)
- Telegram bot created (@BotFather)

## Step 1: Install Dependencies

### Node.js dependencies (for CDK):
```bash
npm install
```

### Python dependencies (for Lambda):
```bash
cd lambda
pip install -r requirements.txt
cd ..
```

This will download and install:
- **boto3** - AWS SDK for Python
- **botocore** - AWS API client (dependency)
- Plus all transitive dependencies (certifi, dateutil, etc.)

## Step 2: Configure Your Settings

```bash
# Copy the example config
cp cdk.json.example cdk.json

# Edit with your settings
# (Use your favorite editor - VS Code, nano, etc.)
```

### In `cdk.json`, update:
```json
{
  "context": {
    "telegramBotToken": "YOUR_BOT_TOKEN_HERE",
    "allowedUserIds": "YOUR_USER_ID_HERE",
    "environmentMap": {
      "prod": {
        "ecs_cluster": "your-cluster-name",
        "rds_instances": "your-db-instance-id"
      }
    },
    "accessPolicy": {
      "YOUR_USER_ID": {
        "envs": ["prod"]
      }
    }
  }
}
```

## Step 3: Deploy to AWS

```bash
npm run deploy
```

The deployment will:
1. Build the TypeScript code
2. Package the Python Lambda function with dependencies
3. Create all AWS resources
4. Output the webhook URL

## Step 4: Register Webhook with Telegram

After deployment, you'll see output like:
```
WebhookUrl = https://xxxxx.execute-api.ap-south-1.amazonaws.com/telegram/webhook
```

Register this with Telegram BotFather:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<WEBHOOK_URL>"
```

## What Gets Installed?

When you run `pip install -r requirements.txt`, you get:

| Package | Purpose | Size |
|---------|---------|------|
| boto3 | AWS SDK | ~20MB |
| botocore | AWS API client | ~15MB |
| certifi | SSL certificates | ~1MB |
| dateutil | Date utilities | ~0.5MB |
| charset_normalizer | Text encoding | ~2MB |
| idna | Domain encoding | ~0.5MB |
| jmespath | JSON queries | ~0.5MB |
| s3transfer | S3 transfers | ~1MB |

**Total: ~40-50MB** (these are temporary during development)

## What's NOT in GitHub?

These files are generated locally and NOT pushed to GitHub:
- `lambda/boto3/` 
- `lambda/botocore/`
- `lambda/certifi/`
- All other `lambda/*.dist-info/` folders
- `node_modules/`
- `cdk.out/`
- `cdk.json` (use `cdk.json.example` instead)

This keeps the repo size small (~5MB instead of 100MB+)

## Troubleshooting

### "boto3 not found" error
```bash
# Make sure you're in the right directory and installed dependencies
cd lambda
pip install -r requirements.txt
cd ..
```

### "Missing cdk.json" error
```bash
# Copy the example first
cp cdk.json.example cdk.json
# Then edit it with your secrets
```

### Deployment fails with permission errors
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Should show your AWS account and user
```

## Development

### Test locally:
```bash
# Run the handler with test event
python lambda/handler.py
```

### View logs:
```bash
aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-* --follow
```

### Update code and redeploy:
```bash
# Make changes to lambda/handler.py
# Then redeploy
npm run deploy
```

---

**First time?** Start with the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
