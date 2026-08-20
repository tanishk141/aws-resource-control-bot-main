# 🚀 AWS Resource Control Bot - Deployment & Usage Guide

**Status:** ✅ Production Ready | **Date:** August 20, 2026

---

## 📖 Quick Navigation

- **First Time Setup?** → [Initial Setup](#initial-setup)
- **Add More Users?** → [Multi-User Setup](#multi-user-setup)
- **Deploy Changes?** → [Deployment](#deployment)
- **Having Issues?** → [Troubleshooting](#troubleshooting)
- **Technical Details?** → [Architecture](#architecture)

---

## 🎯 What This Bot Does

Control your AWS production resources with simple Telegram buttons:

| Action | What Happens |
|--------|--------------|
| **▶️ START** | Starts all ECS services + RDS database |
| **⏹️ STOP** | Stops all ECS services + RDS database |
| **📊 STATUS** | Shows if services/database are running |
| **📋 HISTORY** | See last 10 actions with timestamps |

---

## ⚡ Initial Setup

### Prerequisites
- Node.js 14+ installed
- AWS credentials configured (`aws configure`)
- Telegram bot created (@BotFather)
- Access to AWS console

### One-Time Setup (5 minutes)

```bash
# 1. Install dependencies
npm install

# 2. Get your Telegram User ID
# Search: @userinfobot in Telegram
# Copy the number shown

# 3. Edit cdk.json
# Replace YOUR_USER_ID with the number from step 2
{
  "context": {
    "telegramBotToken": "your-bot-token",
    "telegramWebhookSecret": "your-secret",
    "allowedUserIds": "YOUR_USER_ID",
    "region": "ap-south-1",
    "clusterName": "your-ecs-cluster",
    "dbInstanceId": "your-rds-instance"
  }
}

# 4. Deploy
npm run deploy

# 5. Test in Telegram
# Search: @resource_control_bot
# Send any message and click buttons
```

---

## 👥 Multi-User Setup

### Add More Users (Fast Method - 5 minutes)

```powershell
# Get Telegram User IDs from your team
# Each person: Search @userinfobot in Telegram, copy their number

# Add users with script:
.\add-users.ps1 111111111 222222222 333333333

# When prompted, type: y
# Wait 3-5 minutes for deployment
```

### Add Users (Manual Method - 5 minutes)

```bash
# 1. Edit cdk.json
# Find: "allowedUserIds": "YOUR_ID"
# Change to:
"allowedUserIds": "YOUR_ID,USER2_ID,USER3_ID,USER4_ID"

# 2. Deploy
npm run deploy

# 3. Wait 3-5 minutes
# 4. Users can now use the bot
```

### How to Get Team Member IDs

**Tell them:**
1. Open Telegram
2. Search for `@userinfobot`
3. Click START
4. Copy the "User ID:" number
5. Send it to you

**Example:** They send you `111111111`

---

## 🚀 Deployment

### Deploy Your Changes

```bash
# After editing code or config:
npm run deploy

# Monitor deployment:
aws cloudformation describe-stacks \
  --stack-name TelegramResourceControlBotStack \
  --region ap-south-1 \
  --query 'Stacks[0].StackStatus'
```

**Expected output:** `UPDATE_COMPLETE` (3-5 minutes)

### Rollback (if something breaks)

```bash
# Revert to previous deployment:
git checkout cdk.json
npm run deploy
```

---

## 🔧 Configuration

### Edit cdk.json

```json
{
  "context": {
    // Your Telegram bot token (from @BotFather)
    "telegramBotToken": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    
    // Webhook secret (random string for security)
    "telegramWebhookSecret": "your-secret-key-here",
    
    // Authorized users (comma-separated)
    "allowedUserIds": "155604932,111111111,222222222",
    
    // AWS region
    "region": "ap-south-1",
    
    // ECS cluster name
    "clusterName": "your-cluster-name",
    
    // RDS instance ID
    "dbInstanceId": "your-db-instance-id"
  }
}
```

---

## 📊 Monitoring

### View Real-Time Logs

```bash
aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-yB0Q2KfVLm34 \
  --region ap-south-1 --follow
```

### View Audit History

```bash
aws dynamodb scan \
  --table-name TelegramResourceControlBotAudit \
  --region ap-south-1
```

### Check Bot Webhook Status

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
```

---

## 🏗️ Project Structure

```
aws-resource-control-bot/
├── lambda/                    # Bot logic (Python)
│   ├── handler.py            # Main handler
│   └── requirements.txt       # Dependencies
├── lib/                       # Infrastructure (TypeScript)
│   └── telegram-resource-control-bot-stack.ts
├── cdk.json                   # Configuration
├── package.json              # Dependencies
├── DEPLOYMENT_GUIDE.md       # This file
├── ARCHITECTURE.md           # Technical details
└── add-users.ps1             # Batch user add script
```

---

## 🐛 Troubleshooting

### Bot Not Responding

```bash
# 1. Check webhook status
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"

# 2. View logs
aws logs tail ... --follow

# 3. Verify Lambda is configured
aws lambda get-function \
  --function-name TelegramResourceControlBotStack-BotFunction-XXX \
  --region ap-south-1
```

### User Says "Not Authorized"

1. Verify their Telegram ID with `@userinfobot`
2. Check cdk.json has their ID
3. Confirm deployment finished: `npm run deploy`
4. Wait 2-3 minutes and try again

### Actions Fail (ECS/RDS)

```bash
# 1. Verify cluster exists
aws ecs list-clusters --region ap-south-1

# 2. Verify instance exists
aws rds describe-db-instances --region ap-south-1

# 3. Check Lambda IAM permissions
aws iam get-role-policy \
  --role-name TelegramResourceControlBotStack-BotFunctionRole-XXX \
  --policy-name XXX \
  --region ap-south-1
```

### Deployment Fails

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify CDK is updated
npm update -g aws-cdk

# Try deploy again
npm run deploy
```

---

## 💡 Common Tasks

### Change ECS Cluster

```json
{
  "context": {
    "clusterName": "new-cluster-name"
  }
}
```
Then: `npm run deploy`

### Change RDS Instance

```json
{
  "context": {
    "dbInstanceId": "new-db-instance-id"
  }
}
```
Then: `npm run deploy`

### Add/Remove Users

Edit `allowedUserIds` in cdk.json, then `npm run deploy`

### View Commands Available

```bash
# Bot supports these commands:
/start   - Show menu
/help    - Show help
/status  - Check status
/history - View audit log

# Or click buttons in Telegram UI
```

---

## 📈 Costs

Estimated monthly cost: **$0.50 - $2.00**

Breakdown:
- Lambda: ~$0.20 (free tier covers most)
- API Gateway: ~$0.35
- DynamoDB: ~$0.25 (free tier covers)
- CloudWatch Logs: Included

---

## 🔐 Security

✅ **User Authorization:** Only allowed users can control resources  
✅ **Webhook Validation:** Telegram webhook verified  
✅ **Audit Trail:** All actions logged to DynamoDB  
✅ **IAM Permissions:** Least privilege role for Lambda  
✅ **No Secrets in Code:** All stored in AWS Secrets Manager  

---

## 📞 Support Checklist

If something doesn't work:

- [ ] Check logs: `aws logs tail ... --follow`
- [ ] Verify webhook: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- [ ] Confirm deployment: `npm run deploy`
- [ ] Check IAM permissions in AWS console
- [ ] Verify resources exist (cluster, DB instance)
- [ ] Ensure user ID is in cdk.json
- [ ] Redeploy: `npm run deploy`

---

## 🎓 Technical Details

See **ARCHITECTURE.md** for:
- How the bot processes commands
- Data flow diagrams
- Response formatting
- Error handling
- Performance characteristics

---

## 📝 Next Steps

1. ✅ Follow Initial Setup above
2. ✅ Test in Telegram
3. ✅ Add team members if needed
4. ✅ Monitor logs
5. ✅ Set up alerts (optional)

---

## 🎉 You're Ready!

Your bot is production-ready. Open Telegram and enjoy!

**Questions?** Check the troubleshooting section or review ARCHITECTURE.md for technical details.

---

**Last Updated:** August 20, 2026  
**Status:** Production Ready ✅
