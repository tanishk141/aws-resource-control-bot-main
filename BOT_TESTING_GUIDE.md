# Telegram ECS/RDS Control Bot — Testing Guide

## Status: ✅ Deployed and Ready

Your bot is now deployed with a simplified interface showing only the essential controls for your production environment.

### Quick Reference
- **Bot Token**: `8892548119:AAGUKu48ctAbxiWi0tTlzTTqQvoaHXLoT8E`
- **Telegram User ID**: `155604932`
- **Authorized User**: ✅ Configured
- **Environment**: `prod` (single production environment)
- **Webhook URL**: `https://eaains9gwh.execute-api.ap-south-1.amazonaws.com/telegram/webhook`

---

## How to Test

### Step 1: Open Telegram
1. Search for your bot or open this link: https://t.me/resource_control_bot
2. Send `/start` to initialize

### Step 2: You Should See
The bot responds with help information and a button to open the menu.

### Step 3: Test Commands

**Via Buttons (Easiest):**
1. Send `/menu`
2. You'll see buttons:
   - **▶️ Start Prod** - Starts production ECS + RDS
   - **⏹️ Stop Prod** - Stops production ECS + RDS
   - **📊 Status Prod** - Shows current status
   - **📋 Audit** - Shows recent actions
   - **ℹ️ Help** - Shows help

**Via Text Commands:**
- `/start` - Start production
- `/stop` - Stop production
- `/status` - Check production status
- `/menu` - Show button menu
- `/audit` - View recent actions
- `/help` - Show help

---

## What Each Button Does

### ▶️ Start Prod
- Starts all ECS services in the `telegram-bot-cluster`
- Starts the `database-1` RDS instance
- Sets ECS desiredCount to 1

### ⏹️ Stop Prod
- Stops all ECS services in the `telegram-bot-cluster`
- Stops the `database-1` RDS instance
- Sets ECS desiredCount to 0

### 📊 Status Prod
Shows:
- ECS Service names
- Running vs Desired count for each service
- RDS instance status
- RDS endpoint

### 📋 Audit
Shows last 10 actions with timestamps:
- User who performed the action
- Action (start/stop/status)
- Result (success/error)
- Timestamp (UTC)

---

## Debugging

### If Authorization Fails
**Message**: "You are not authorized"

**Check:**
1. Environment variables in Lambda:
   ```bash
   aws lambda get-function-configuration \
     --function-name TelegramResourceControlBo-TelegramResourceControlB-ISLw9qFtPS5v \
     --region ap-south-1 \
     | grep -A5 Environment
   ```

2. Verify ALLOWED_USER_IDS is set to: `155604932`

3. Get your Telegram user ID:
   - Send any message to the bot
   - Check CloudWatch logs

### If Buttons Don't Work
Check CloudWatch logs:
```bash
aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-yB0Q2KfVLm34 \
  --region ap-south-1 \
  --follow
```

### If Actions Fail
Errors appear in the bot response. Common causes:
- ECS cluster name incorrect
- RDS instance name incorrect
- AWS credentials missing permissions
- ECS service doesn't exist

---

## Configuration

### Current Setup (cdk.json)
```json
{
  "context": {
    "telegramBotToken": "8892548119:AAGUKu48ctAbxiWi0tTlzTTqQvoaHXLoT8E",
    "allowedUserIds": "155604932",
    "environmentMap": {
      "prod": {
        "ecs_cluster": "telegram-bot-cluster",
        "rds_instances": "database-1"
      }
    }
  }
}
```

### To Add More Users
Edit `cdk.json` and change:
```json
"allowedUserIds": "155604932,OTHER_USER_ID"
```

Then redeploy:
```bash
npm run deploy
```

### To Add More Environments
Edit `cdk.json` and add:
```json
"environmentMap": {
  "prod": {...},
  "staging": {
    "ecs_cluster": "staging-cluster",
    "rds_instances": "staging-db"
  }
}
```

Then update the handler buttons to include new environments, or the menu will still show only Prod.

---

## Architecture

```
Telegram User
    ↓
Telegram Bot API
    ↓
API Gateway (HTTP)
    ↓
Lambda Function
    ├→ ECS (start/stop/describe)
    ├→ RDS (start/stop/describe)
    └→ DynamoDB (audit trail)
    ↓
Response back to Telegram
```

---

## Monitoring

### View Recent Logs
```bash
aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-yB0Q2KfVLm34 \
  --region ap-south-1 \
  --since 10m \
  --format short
```

### Query Audit Trail
```bash
aws dynamodb scan \
  --table-name TelegramResourceControlBotAudit \
  --region ap-south-1 \
  --limit 10
```

### Lambda Function Status
```bash
aws lambda get-function-configuration \
  --function-name TelegramResourceControlBo-TelegramResourceControlB-ISLw9qFtPS5v \
  --region ap-south-1
```

---

## Next Steps

1. **Test the bot** - Send commands from Telegram
2. **Verify ECS cluster exists** - Check AWS ECS console for `telegram-bot-cluster`
3. **Verify RDS instance exists** - Check AWS RDS console for `database-1`
4. **Check logs** - Monitor CloudWatch for any errors
5. **Review audit trail** - See who did what and when

---

## Support

If the bot doesn't respond:
1. Check if webhook is registered: https://api.telegram.org/bot8892548119:AAGUKu48ctAbxiWi0tTlzTTqQvoaHXLoT8E/getWebhookInfo
2. Check Lambda logs
3. Verify environment variables
4. Ensure AWS credentials have proper permissions

