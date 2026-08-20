# 🤖 AWS Resource Control Bot

Control your AWS production resources (ECS + RDS) with a simple Telegram bot.

## 🚀 Quick Start

**👉 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** ← Start here for setup and deployment

---

## ⚡ What This Bot Does

One-click control of production resources:

| Action | What Happens |
|--------|--------------|
| **▶️ START** | Starts ECS services + RDS database |
| **⏹️ STOP** | Stops ECS services + RDS database |
| **📊 STATUS** | Check if services/database are running |
| **📋 HISTORY** | View last 10 actions with timestamps |

## 📂 Project Structure

```
.
├── lambda/
│   ├── handler.py              # Bot logic (Python)
│   └── requirements.txt         # Dependencies
├── lib/
│   └── telegram-resource-control-bot-stack.ts  # Infrastructure (TypeScript)
├── cdk.json                    # Configuration
├── package.json                # Dependencies
├── DEPLOYMENT_GUIDE.md         # ⭐ START HERE
├── ARCHITECTURE.md             # Technical details
├── BOT_TESTING_GUIDE.md        # Testing instructions
└── README.md                   # This file
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_GUIDE.md** | Setup, deployment, multi-user, troubleshooting |
| **ARCHITECTURE.md** | Technical architecture & design |
| **BOT_TESTING_GUIDE.md** | How to test the bot |

## 🔧 Quick Commands

```bash
# First time setup
npm install
npm run deploy

# Add team members (edit IDs first)
.\add-users.ps1 ID1 ID2 ID3

# Deploy changes
npm run deploy

# View logs
aws logs tail TelegramResourceControlBotStack-BotLogGroup* --region ap-south-1 --follow

# Check deployment status
aws cloudformation describe-stacks --stack-name TelegramResourceControlBotStack --region ap-south-1 --query 'Stacks[0].StackStatus'
```

## 🎯 Get Started

1. **Read:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. **Configure:** Edit `cdk.json` with your settings
3. **Deploy:** Run `npm run deploy`
4. **Test:** Open Telegram and find `@resource_control_bot`

## 🔐 Security

- ✅ User authorization via allowlist
- ✅ Webhook validation from Telegram
- ✅ All actions audited to DynamoDB
- ✅ IAM least privilege permissions
- ✅ No secrets in code

## 💰 Estimated Cost

**~$0.50-2.00/month** (mostly free tier)

---

**Ready to deploy?** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
