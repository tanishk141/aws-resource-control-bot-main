# Lambda Handler Architecture

## Overview

The Lambda handler (`lambda/handler.py`) implements unified resource control for both ECS and RDS using the exact same patterns you specified.

## Key Functions

### 1. ECS Cluster Handler

```python
def handle_ecs_clusters(action: str, clusters: List[str]) -> List[Dict[str, Any]]:
```

**What it does:**
- Accepts action ("start" or "stop") and list of cluster names
- Lists all services in each cluster using ECS API
- Updates desired task count:
  - **Start**: Sets desiredCount = 1 (tasks will spin up)
  - **Stop**: Sets desiredCount = 0 (tasks will terminate)
- Returns detailed results with success/error status

**Features:**
- Handles pagination for clusters with many services
- Error handling per service (won't stop if one fails)
- DRY_RUN mode support (logs without making changes)
- Detailed error messages in response

### 2. RDS Instance Handler

```python
def handle_rds(action: str, instance_ids: List[str]) -> List[Dict[str, Any]]:
```

**What it does:**
- Accepts action ("start" or "stop") and list of instance IDs
- Calls RDS API: `start_db_instance()` or `stop_db_instance()`
- Returns instance status and any errors

**Features:**
- Works with multiple instances
- Returns DB instance status (starting, stopping, available, etc.)
- DRY_RUN mode support
- Error handling with detailed messages

## Telegram Command Routing

### ECS Commands

```
/ecs-start phiquadrate-uat-cluster
    ?
parse_command() extracts: command="/ecs-start", args=["phiquadrate-uat-cluster"]
    ?
handle_ecs_clusters(action="start", clusters=["phiquadrate-uat-cluster"])
    ?
Returns: [{"cluster": "...", "services": [...]}]
    ?
format_ecs_response() formats for Telegram
    ?
send_telegram_message() sends to user
```

### RDS Commands

```
/rds-stop phiquadrate-uat-db
    ?
parse_command() extracts: command="/rds-stop", args=["phiquadrate-uat-db"]
    ?
handle_rds(action="stop", instance_ids=["phiquadrate-uat-db"])
    ?
Returns: [{"id": "phiquadrate-uat-db", "status": "stopping"}]
    ?
format_rds_response() formats for Telegram
    ?
send_telegram_message() sends to user
```

## Response Formatting

### ECS Response Example

```
<b>ECS Cluster START Report</b>

<b>Cluster:</b> phiquadrate-uat-cluster
<b>Services (3):</b>
  • service-api: ? Successfully updated desiredCount to 1
  • service-worker: ? Successfully updated desiredCount to 1
  • service-scheduler: ? Successfully updated desiredCount to 1
```

### RDS Response Example

```
<b>RDS Instance STOP Report</b>

  • phiquadrate-uat-db: ? Status: stopping
```

## Unified Processing Logic

Both ECS and RDS use the same unified flow:

1. **Parse Command** ? Extract resource name/ID
2. **Validate User** ? Check if authorized
3. **Execute Operation** ? Call AWS API
4. **Log Results** ? DynamoDB audit trail
5. **Format Response** ? User-friendly Telegram message
6. **Send Response** ? Back to user

## Audit Logging

All operations logged to DynamoDB:

```python
log_audit(
    user_id=123456789,
    command="/ecs-start",
    resource_type="ecs",
    resource_id="phiquadrate-uat-cluster",
    action="start",
    status="success",
    details=json.dumps(results)
)
```

Audit table schema:
```
pk: USER#123456789
sk: TIMESTAMP#1692907200#ecs
command: /ecs-start
resource_type: ecs
resource_id: phiquadrate-uat-cluster
action: start
status: success
details: {...}
timestamp: 1692907200
ttl: 1702747200 (90 days from now)
```

## Error Handling

### User Not Authorized
```
? You are not authorized to use this bot.
```

### Invalid Command
```
? Invalid command. Use /help for available commands.
```

### Missing Arguments
```
? Please specify a cluster name.
Usage: /ecs-start <cluster_name>
```

### Operation Failed
```
? Error: Failed to update service xyz: <error_details>
```

## Configuration-Driven Resources

Resources are loaded from environment variable (set by CDK):

```json
{
  "ecsClusters": [
    {"name": "phiquadrate-uat-cluster", "region": "us-east-1"},
    {"name": "phiquadrate-prod-cluster", "region": "us-east-1"}
  ],
  "rdsInstances": [
    {"name": "phiquadrate-uat-db", "region": "us-east-1"},
    {"name": "phiquadrate-prod-db", "region": "us-east-1"}
  ]
}
```

This shows in `/help` command for user reference.

## DRY_RUN Mode

When `DRY_RUN=true`:
- Commands are validated
- APIs are NOT called
- Response shows "[DRY RUN] Would..." messages
- Useful for testing without affecting resources

Example:
```
[DRY RUN] Would set Service: service-api (Cluster: phiquadrate-uat-cluster) to desiredCount: 1
```

## Performance Characteristics

| Operation | Typical Duration | Timeout |
|-----------|------------------|---------|
| ECS list services | 100-500ms | 60s Lambda timeout |
| ECS update service | 200-1000ms | 60s Lambda timeout |
| RDS start/stop | 500-2000ms | 60s Lambda timeout |

Lambda timeout is 60 seconds (configurable in CDK stack).

## Scalability

- **ECS**: Handles 100s of services (pagination support)
- **RDS**: Handles multiple instances in parallel
- **Concurrency**: API Gateway + Lambda auto-scale
- **Storage**: DynamoDB on-demand (auto-scales)

## Security Measures

1. **User Authorization**: Telegram user ID allowlist
2. **API Permissions**: IAM least-privilege (only start/stop)
3. **Audit Trail**: DynamoDB logs all actions
4. **No Secret Leaks**: Tokens excluded from CloudWatch
5. **Always 200**: Lambda returns 200 to prevent Telegram retries

## Testing Commands

**Manual test via Lambda console:**

```json
{
  "body": "{\"message\":{\"from\":{\"id\":123456789},\"chat\":{\"id\":123456789},\"text\":\"/help\"}}"
}
```

**Real Telegram test:**

1. Start bot: `/help`
2. Start ECS: `/ecs-start phiquadrate-uat-cluster`
3. Stop ECS: `/ecs-stop phiquadrate-uat-cluster`
4. Start RDS: `/rds-start phiquadrate-uat-db`
5. Stop RDS: `/rds-stop phiquadrate-uat-db`

---

**Architecture**: Unified single-Lambda resource control
**Status**: ? Production-ready
