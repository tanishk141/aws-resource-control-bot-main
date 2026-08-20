# 🤖 Telegram ECS/RDS Control Bot

Control your AWS ECS clusters and RDS databases directly from Telegram with simple button clicks.

## ⚡ What It Does

- **▶️ START** - Start all ECS services + RDS database
- **⏹️ STOP** - Stop all ECS services + RDS database  
- **📊 STATUS** - Check if services/database are running
- **📋 HISTORY** - View audit trail of actions

## 🏗️ Architecture

```
Telegram → API Gateway → Lambda Function → ECS/RDS
                              ↓
                          DynamoDB (Audit Logs)
```

**AWS Resources Deployed:**
- Lambda Function (Python, 512MB, 300s timeout)
- API Gateway HTTP API (webhook endpoint)
- DynamoDB Table (audit logs)
- CloudWatch Logs (30 day retention)
- IAM Role (with ECS/RDS permissions)

## 📋 Prerequisites

- Node.js 14+
- Python 3.12
- AWS account with credentials configured
- Telegram bot (create via @BotFather)

## 🚀 Setup (5 Steps)

### Step 1: Clone & Install

```bash
git clone https://github.com/tanishk141/aws-resource-control-bot-main.git
cd aws-resource-control-bot-main

# Install Node dependencies
npm install

# Install Python dependencies
cd lambda
pip install -r requirements.txt
cd ..
```

### Step 2: Configure

```bash
# Copy example config
cp cdk.json.example cdk.json

# Edit with your settings
nano cdk.json  # or use your favorite editor
```

**Required in `cdk.json`:**
```json
{
  "context": {
    "telegramBotToken": "YOUR_BOT_TOKEN",
    "allowedUserIds": "YOUR_TELEGRAM_USER_ID",
    "environmentMap": {
      "prod": {
        "ecs_cluster": "your-cluster-name",
        "rds_instances": "your-db-instance-id"
      }
    },
    "accessPolicy": {
      "YOUR_TELEGRAM_USER_ID": {
        "envs": ["prod"]
      }
    }
  }
}
```

**How to find values:**
- **Telegram Bot Token:** @BotFather → /newbot → copy token
- **Telegram User ID:** Message @userinfobot in Telegram → copy ID
- **ECS Cluster:** `aws ecs list-clusters --region ap-south-1`
- **RDS Instance:** `aws rds describe-db-instances --region ap-south-1`

### Step 3: Deploy

```bash
npm run deploy
```

This creates all AWS resources. Watch for the output:
```
WebhookUrl = https://xxxxx.execute-api.ap-south-1.amazonaws.com/telegram/webhook
```

### Step 4: Register Webhook

Copy the WebhookUrl from deployment output, then:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<WEBHOOK_URL>"
```

Replace `<YOUR_TOKEN>` with your Telegram bot token.

### Step 5: Test

Open Telegram, find your bot, send any message. You should see the menu with buttons.

---

## 📝 Configuration Details

### `cdk.json` Structure

```json
{
  "context": {
    "telegramBotToken": "string - Bot token from @BotFather",
    "allowedUserIds": "string - Comma-separated Telegram user IDs",
    "environmentMap": {
      "prod": {
        "ecs_cluster": "string - ECS cluster name",
        "rds_instances": "string - RDS instance identifier"
      }
    },
    "accessPolicy": {
      "USER_ID": {
        "envs": ["list of accessible environments"]
      }
    }
  }
}
```

### Multiple Environments

```json
{
  "environmentMap": {
    "prod": {
      "ecs_cluster": "prod-cluster",
      "rds_instances": "prod-db"
    },
    "staging": {
      "ecs_cluster": "staging-cluster",
      "rds_instances": "staging-db"
    }
  },
  "accessPolicy": {
    "USER_1": { "envs": ["prod"] },
    "USER_2": { "envs": ["prod", "staging"] }
  }
}
```

---

## 🔄 Development Workflow

### Update Bot Code

1. Edit `lambda/handler.py`
2. Redeploy: `npm run deploy`
3. Changes live in 1-2 minutes

### Add New Dependencies

```bash
# Add to lambda/requirements.txt
echo "new-package>=1.0.0" >> lambda/requirements.txt

# Install locally
cd lambda
pip install -r requirements.txt
cd ..

# Redeploy
npm run deploy
```

### View Logs

```bash
aws logs tail TelegramResourceControlBotStack-BotLogGroup* --follow --region ap-south-1
```

### Check Audit Trail

```bash
aws dynamodb scan \
  --table-name TelegramResourceControlBotAudit \
  --region ap-south-1 \
  --output table
```

---

## 🛑 Teardown

Remove all AWS resources:

```bash
npm run cdk -- destroy
```

Confirm when prompted. This removes Lambda, API Gateway, DynamoDB, and other resources.

---

## 🔐 Security

- ✅ User authorization (only allowed users can control resources)
- ✅ Per-environment access control (users can be limited to specific environments)
- ✅ Audit logging (all actions tracked in DynamoDB)
- ✅ Webhook validation (Telegram webhook secret)
- ✅ Least privilege IAM role (only ECS/RDS permissions)
- ✅ Secrets in `.gitignore` (cdk.json not pushed to GitHub)

---

## 📊 Monitoring

### Lambda Metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --start-time 2026-08-20T00:00:00Z \
  --end-time 2026-08-21T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region ap-south-1
```

### CloudWatch Logs

```bash
# Last 10 log entries
aws logs tail TelegramResourceControlBotStack-BotLogGroup* --region ap-south-1

# Follow logs in real-time
aws logs tail TelegramResourceControlBotStack-BotLogGroup* --follow --region ap-south-1
```

---

## 🐛 Troubleshooting

### Bot Not Responding

1. Check webhook is registered:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

2. Check Lambda logs:
   ```bash
   aws logs tail TelegramResourceControlBotStack-BotLogGroup* --follow --region ap-south-1
   ```

3. Verify user ID is in `cdk.json`

### "User Not Authorized"

- Check `allowedUserIds` in `cdk.json`
- Verify your Telegram user ID with @userinfobot
- Redeploy after editing: `npm run deploy`

### Actions Fail (ECS/RDS)

- Check cluster/DB exist: `aws ecs list-clusters`, `aws rds describe-db-instances`
- Verify names in `cdk.json` are correct
- Check Lambda IAM role has permissions (automatically granted by CDK)

### Deployment Fails

```bash
# Clear cache and retry
rm -rf cdk.out
npm run deploy
```

---

## 💰 Cost Estimate

| Service | Cost | Notes |
|---------|------|-------|
| Lambda | ~$0.20 | Free tier covers most |
| API Gateway | ~$0.35 | Per million requests |
| DynamoDB | ~$0.25 | Free tier covers most |
| CloudWatch | Included | Logs included |
| **Total/month** | **~$0.50-$2** | Mostly free tier |

---

## 📚 Project Structure

```
.
├── lambda/
│   ├── handler.py          # Bot logic
│   └── requirements.txt     # Python dependencies
├── lib/
│   └── telegram-resource-control-bot-stack.ts  # Infrastructure
├── bin/
│   └── app.ts              # CDK entry point
├── cdk.json.example        # Config template
├── package.json            # Node dependencies
├── README.md               # This file
└── .gitignore              # Git exclude rules
```

---

## 🔄 Start/Stop Sequence

### START
1. RDS starts
2. Wait for RDS available
3. ECS services start
4. Wait for ECS services stable

### STOP
1. ECS services stop
2. Wait for all ECS tasks = 0
3. RDS stops
4. Wait for RDS stopped

---

## 📞 Support

- Check logs: `aws logs tail TelegramResourceControlBotStack-BotLogGroup* --follow`
- Verify config: `cat cdk.json`
- Check AWS credentials: `aws sts get-caller-identity`
- Verify resources exist: `aws ecs list-clusters`, `aws rds describe-db-instances`

---

## 📄 License

MIT

---

**Made with ❤️ for AWS Resource Control**
