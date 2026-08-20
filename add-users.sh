#!/bin/bash

# Script to easily add multiple users to the bot
# Usage: ./add-users.sh 155604932 987654321 123456789

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 Production Control Bot - Add Multiple Users${NC}\n"

# Check if user provided any IDs
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No user IDs provided${NC}"
    echo -e "${YELLOW}Usage: ./add-users.sh 155604932 987654321 123456789${NC}"
    echo ""
    echo "Get user IDs by:"
    echo "  1. User sends /start to bot"
    echo "  2. Check CloudWatch logs:"
    echo "     aws logs tail TelegramResourceControlBotStack-BotLogGroup11FD2D9F-yB0Q2KfVLm34 --region ap-south-1 --follow"
    echo "  3. Look for: 'Checking authorization for user_id=XXX'"
    exit 1
fi

# Join all provided IDs with commas
USER_IDS=$(IFS=,; echo "$*")

echo -e "${BLUE}Adding users: ${NC}${USER_IDS}\n"

# Read current cdk.json
CDK_FILE="cdk.json"

if [ ! -f "$CDK_FILE" ]; then
    echo -e "${RED}Error: $CDK_FILE not found${NC}"
    exit 1
fi

# Backup original file
cp "$CDK_FILE" "$CDK_FILE.backup"
echo -e "${GREEN}✓ Backup created: $CDK_FILE.backup${NC}\n"

# Update the allowedUserIds (works on macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/\"allowedUserIds\": \"[^\"]*\"/\"allowedUserIds\": \"$USER_IDS\"/" "$CDK_FILE"
else
    # Linux
    sed -i "s/\"allowedUserIds\": \"[^\"]*\"/\"allowedUserIds\": \"$USER_IDS\"/" "$CDK_FILE"
fi

echo -e "${GREEN}✓ Updated cdk.json with new user IDs${NC}\n"

# Show what was updated
echo -e "${BLUE}New configuration:${NC}"
grep "allowedUserIds" "$CDK_FILE"
echo ""

# Ask if user wants to deploy
echo -e "${YELLOW}Do you want to deploy now? (y/n)${NC}"
read -r DEPLOY

if [[ "$DEPLOY" == "y" || "$DEPLOY" == "Y" ]]; then
    echo -e "\n${BLUE}Deploying...${NC}\n"
    npm run deploy
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ Deployment successful!${NC}"
        echo -e "${GREEN}All users can now use the bot.${NC}\n"
    else
        echo -e "\n${RED}✗ Deployment failed${NC}"
        echo -e "${YELLOW}To retry, run: npm run deploy${NC}\n"
    fi
else
    echo -e "\n${YELLOW}Skipped deployment.${NC}"
    echo -e "${BLUE}To deploy later, run:${NC} npm run deploy\n"
fi

echo -e "${GREEN}Done!${NC}"
