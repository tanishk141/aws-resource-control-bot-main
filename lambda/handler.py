"""
Telegram ECS/RDS Control Bot — Lambda Handler
Handles webhook events from Telegram, manages ECS clusters and RDS instances.
Simple interface: Just Start/Stop/Status for production environment.
"""

import json
import os
import logging
import urllib.request
import time
import boto3
from datetime import datetime
from typing import Dict, List, Optional

# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Configuration ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = [uid.strip() for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",") if uid.strip()]
ENVIRONMENT_MAP = json.loads(os.environ.get("ENVIRONMENT_MAP", "{}"))
ACCESS_POLICY = json.loads(os.environ.get("ACCESS_POLICY", "{}"))

logger.info("===== BOT CONFIGURATION =====")
logger.info("TELEGRAM_BOT_TOKEN: %s***", TELEGRAM_BOT_TOKEN[:20] if TELEGRAM_BOT_TOKEN else "NOT SET")
logger.info("ALLOWED_USER_IDS: %s", ALLOWED_USER_IDS)
logger.info("ACCESS_POLICY: %s", "configured" if ACCESS_POLICY else "not configured")
logger.info("ENVIRONMENT_MAP: %s", ENVIRONMENT_MAP)
logger.info("=============================")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
REGION = os.environ.get("AWS_REGION_NAME", os.environ.get("AWS_REGION", "ap-south-1"))
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "TelegramResourceControlBotAudit")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "resource_control_bot")
LAMBDA_ARN = ""

# ── AWS Clients ──────────────────────────────────────────────
ecs_client = boto3.client("ecs", region_name=REGION)
rds_client = boto3.client("rds", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_audit_table():
    if AUDIT_TABLE:
        return dynamodb.Table(AUDIT_TABLE)
    return None

# ══════════════════════════════════════════════════════════════
#  Authorization
# ══════════════════════════════════════════════════════════════

def is_user_authorized(user_id: str) -> bool:
    """Check if a user is authorized to use the bot."""
    if ALLOWED_USER_IDS:
        return user_id in ALLOWED_USER_IDS
    logger.warning("No authorization configured (empty ALLOWED_USER_IDS)")
    return False

def get_user_accessible_envs(user_id: str) -> List[str]:
    """Get list of environments accessible to a specific user."""
    if ACCESS_POLICY and user_id in ACCESS_POLICY:
        return ACCESS_POLICY[user_id].get("envs", [])
    
    if is_user_authorized(user_id):
        return list(ENVIRONMENT_MAP.keys())
    return []

def can_access_env(user_id: str, env_name: str) -> bool:
    """Check if a user can access a specific environment."""
    return env_name in get_user_accessible_envs(user_id)

# ══════════════════════════════════════════════════════════════
#  Telegram API helpers
# ══════════════════════════════════════════════════════════════

def telegram_request(method: str, payload: dict) -> dict:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{TELEGRAM_API_URL}/{method}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error("Telegram API %s failed: %s", method, str(e))
        return {}

def send_message(chat_id: int, text: str, reply_markup: dict = None) -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    return telegram_request("sendMessage", payload)

def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    return telegram_request("editMessageText", payload)

def answer_callback(callback_query_id: str, text: str = "") -> dict:
    payload = {"callback_query_id": callback_query_id}
    if text: payload["text"] = text
    return telegram_request("answerCallbackQuery", payload)

def build_main_menu_keyboard(user_id: str = None) -> dict:
    show_envs = []
    if user_id and ACCESS_POLICY:
        show_envs = get_user_accessible_envs(user_id)
    elif is_user_authorized(user_id) if user_id else True:
        show_envs = ["prod"] if "prod" in ENVIRONMENT_MAP else list(ENVIRONMENT_MAP.keys())
    
    if not show_envs:
        return {
            "inline_keyboard": [
                [{"text": "❓ HELP", "callback_data": "action:help"}],
                [{"text": "📋 HISTORY", "callback_data": "action:audit"}],
            ]
        }
    
    env_name = show_envs[0] if show_envs else "prod"
    return {
        "inline_keyboard": [
            [
                {"text": "▶️ START", "callback_data": f"exec:start:{env_name}"},
                {"text": "⏹️ STOP", "callback_data": f"exec:stop:{env_name}"},
            ],
            [
                {"text": "📊 STATUS", "callback_data": f"exec:status:{env_name}"},
            ],
            [
                {"text": "📋 HISTORY", "callback_data": "action:audit"},
                {"text": "❓ HELP", "callback_data": "action:help"},
            ],
        ]
    }

# ══════════════════════════════════════════════════════════════
#  ECS Helpers
# ══════════════════════════════════════════════════════════════

def get_all_service_arns(cluster_name: str) -> List[str]:
    """Get all service ARNs safely using pagination."""
    arns = []
    paginator = ecs_client.get_paginator('list_services')
    for page in paginator.paginate(cluster=cluster_name):
        arns.extend(page.get("serviceArns", []))
    return arns

def get_all_service_details(cluster_name: str, service_arns: List[str]) -> List[Dict]:
    """Fetch details for all services, handling the AWS 10-item limit."""
    services = []
    for i in range(0, len(service_arns), 10):
        chunk = service_arns[i:i+10]
        resp = ecs_client.describe_services(cluster=cluster_name, services=chunk)
        services.extend(resp.get("services", []))
    return services

# ══════════════════════════════════════════════════════════════
#  ECS/RDS Operations
# ══════════════════════════════════════════════════════════════

def start_ecs_cluster(cluster_name: str) -> Dict:
    """Start all ECS services in a cluster immediately without blocking."""
    try:
        service_arns = get_all_service_arns(cluster_name)
        if not service_arns:
            return {"status": "warning", "message": f"⚠️ No services found in cluster '{cluster_name}'.", "details": []}
        
        updated, errors = [], []
        for arn in service_arns:
            service_name = arn.split("/")[-1]
            try:
                ecs_client.update_service(cluster=cluster_name, service=arn, desiredCount=1)
                updated.append(service_name)
            except Exception as svc_err:
                errors.append(f"{service_name}: {str(svc_err)[:50]}")
        
        if not updated:
            return {"status": "error", "message": "❌ Failed to start any services", "details": errors}
        
        return {
            "status": "success",
            "message": f"✅ Started {len(updated)} service(s)",
            "details": updated,
            "wait_info": {
                "status": "success",
                "message": "⏳ Services starting. They will stabilize once RDS is ready."
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"❌ Failed to start services: {str(e)[:80]}"}

def stop_ecs_cluster(cluster_name: str) -> Dict:
    """Stop all ECS services in a cluster immediately."""
    try:
        service_arns = get_all_service_arns(cluster_name)
        if not service_arns:
            return {"status": "warning", "message": f"⚠️ No services found in cluster '{cluster_name}'.", "details": []}
        
        updated, errors = [], []
        for arn in service_arns:
            service_name = arn.split("/")[-1]
            try:
                ecs_client.update_service(cluster=cluster_name, service=arn, desiredCount=0)
                updated.append(service_name)
            except Exception as svc_err:
                errors.append(f"{service_name}: {str(svc_err)[:50]}")
        
        if not updated:
            return {"status": "error", "message": "❌ Failed to stop any services", "details": errors}
        
        return {
            "status": "success",
            "message": f"✅ Stopped {len(updated)} service(s)",
            "details": updated,
            "wait_info": {
                "status": "success",
                "message": "⏳ Stop command sent to all services."
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"❌ Failed to stop services: {str(e)[:80]}"}

def describe_ecs_cluster(cluster_name: str) -> Dict:
    """Get ECS cluster status with service details."""
    try:
        all_arns = get_all_service_arns(cluster_name)
        if not all_arns:
            return {"status": "success", "services": []}
        
        services_detail = get_all_service_details(cluster_name, all_arns)
        
        services = []
        for svc in services_detail:
            services.append({
                "name": svc["serviceName"],
                "running_count": svc.get("runningCount", 0),
                "desired_count": svc.get("desiredCount", 0),
                "status": svc.get("status", "UNKNOWN"),
                "pending_count": svc.get("pendingCount", 0)
            })
        
        return {"status": "success", "services": services}
    except Exception as e:
        logger.error("Failed to describe ECS cluster: %s", str(e))
        return {"status": "error", "message": str(e)}

def start_rds_instance(instance_id: str) -> Dict:
    """Start an RDS instance immediately and report starting state."""
    try:
        response = rds_client.start_db_instance(DBInstanceIdentifier=instance_id)
        state = response["DBInstance"]["DBInstanceStatus"]
        
        return {
            "status": "success",
            "state": state,
            "wait_info": {
                "status": "success", 
                "message": "⏳ RDS is in starting state. It takes 5 to 10 mins to be available. Check Status for recent updates."
            }
        }
    except Exception as e:
        logger.error("Failed to start RDS: %s", str(e))
        return {"status": "error", "message": str(e)}

def stop_rds_instance(instance_id: str) -> Dict:
    """Stop an RDS instance immediately and report stopping state."""
    try:
        response = rds_client.stop_db_instance(DBInstanceIdentifier=instance_id)
        state = response["DBInstance"]["DBInstanceStatus"]
        
        return {
            "status": "success",
            "state": state,
            "wait_info": {
                "status": "success", 
                "message": "⏳ RDS goes into stopping and will be stopped within 5 - 10 mins."
            }
        }
    except Exception as e:
        logger.error("Failed to stop RDS: %s", str(e))
        return {"status": "error", "message": str(e)}

def describe_rds_instance(instance_id: str) -> Dict:
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
        instance = response["DBInstances"][0]
        return {
            "status": "success",
            "state": instance["DBInstanceStatus"],
            "endpoint": instance.get("Endpoint", {}).get("Address", "N/A"),
            "engine": instance.get("Engine", "N/A"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def orchestrate_start(ecs_cluster: str, rds_instance: str) -> tuple:
    results = {"rds_start": None, "rds_wait": None, "ecs_start": None, "ecs_wait": None}
    
    results["rds_start"] = start_rds_instance(rds_instance)
    results["rds_wait"] = results["rds_start"].get("wait_info", {})
    
    results["ecs_start"] = start_ecs_cluster(ecs_cluster)
    results["ecs_wait"] = results["ecs_start"].get("wait_info", {})
    
    return results

def orchestrate_stop(ecs_cluster: str, rds_instance: str) -> tuple:
    results = {"ecs_stop": None, "ecs_wait": None, "rds_stop": None, "rds_wait": None}
    
    results["ecs_stop"] = stop_ecs_cluster(ecs_cluster)
    results["ecs_wait"] = results["ecs_stop"].get("wait_info", {})
    
    results["rds_stop"] = stop_rds_instance(rds_instance)
    results["rds_wait"] = results["rds_stop"].get("wait_info", {})
    
    return results

def format_orchestration_result(action: str, results: Dict) -> str:
    if action == "start":
        lines = ["🚀 <b>START Sequence</b>\n"]
        if results["rds_start"]:
            lines.append(f"<b>Phase 1: RDS Start</b>")
            if results["rds_start"].get("status") == "success":
                lines.append(f"  ✅ RDS start initiated")
                if results["rds_wait"]: lines.append(f"  {results['rds_wait'].get('message', '')}")
            else:
                lines.append(f"  ❌ {results['rds_start'].get('message', 'Error')}")
        
        lines.append("")
        if results["ecs_start"]:
            lines.append(f"<b>Phase 2: ECS Start</b>")
            if results["ecs_start"].get("status") == "success":
                lines.append(f"  ✅ Started {len(results['ecs_start'].get('details', []))} service(s)")
                if results["ecs_wait"]: lines.append(f"  {results['ecs_wait'].get('message', '')}")
            else:
                lines.append(f"  ❌ {results['ecs_start'].get('message', 'Error')}")
        return "\n".join(lines)
    
    elif action == "stop":
        lines = ["🛑 <b>STOP Sequence</b>\n"]
        if results["ecs_stop"]:
            lines.append(f"<b>Phase 1: ECS Stop</b>")
            if results["ecs_stop"].get("status") == "success":
                lines.append(f"  ✅ Stopped {len(results['ecs_stop'].get('details', []))} service(s)")
                if results["ecs_wait"]: lines.append(f"  {results['ecs_wait'].get('message', '')}")
            else:
                lines.append(f"  ❌ {results['ecs_stop'].get('message', 'Error')}")
        
        lines.append("")
        if results["rds_stop"]:
            lines.append(f"<b>Phase 2: RDS Stop</b>")
            if results["rds_stop"].get("status") == "success":
                lines.append(f"  ✅ RDS stop initiated")
                if results["rds_wait"]: lines.append(f"  {results['rds_wait'].get('message', '')}")
            else:
                lines.append(f"  ❌ {results['rds_stop'].get('message', 'Error')}")
        return "\n".join(lines)

def log_audit(user_id: str, username: str, action: str, env: str, resource: str, result: str, detail: str = "") -> None:
    table = get_audit_table()
    if not table: return
    try:
        table.put_item(Item={
            "pk": f"USER#{user_id}",
            "sk": f"ACTION#{int(time.time() * 1000)}",
            "user_id": user_id, "username": username or "unknown",
            "action": action, "environment": env, "resource": resource,
            "result": result, "detail": detail,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ttl": int(time.time()) + (90 * 86400),
        })
    except Exception as e:
        logger.error("Audit log failed: %s", str(e))

def get_recent_audit(user_id: str = None, limit: int = 10) -> str:
    table = get_audit_table()
    if not table: return "📋 Audit trail not configured."
    try:
        if user_id:
            resp = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq(f"USER#{user_id}"),
                ScanIndexForward=False, Limit=limit,
            )
        else:
            resp = table.scan(Limit=limit * 3)
            resp["Items"] = sorted(resp.get("Items", []), key=lambda x: x.get("sk", ""), reverse=True)[:limit]
        
        items = resp.get("Items", [])
        if not items: return "📋 <b>Recent Actions</b>\n\nNo actions yet."
        
        lines = ["📋 <b>Recent Actions</b>\n"]
        for item in items:
            ts, action, env = str(item.get("timestamp", "?"))[:19], str(item.get("action", "?")), str(item.get("environment", "?"))
            result, username = str(item.get("result", "?")), str(item.get("username", "?"))
            lines.append(f"• <b>{action}</b> <code>{env}</code> → {result}\n  by {username} at {ts}")
        return "\n".join(lines)
    except Exception as e:
        return f"📋 <b>Recent Actions</b>\n\nError loading audit: {str(e)[:50]}"

def format_help_response() -> str:
    return (
        "👋 <b>Welcome to Production Control Bot</b>\n\n"
        "<b>▶️ START</b> - Bring production online\n"
        "<b>⏹️ STOP</b> - Take production offline\n"
        "<b>📊 STATUS</b> - Check if production is running\n"
        "<b>📋 HISTORY</b> - See what was done\n\n"
        "💡 <i>Just tap a button — no commands needed!</i>"
    )

def format_error(message: str) -> str:
    return f"❌ <b>Error</b>\n\n{message}"

def format_status_response(env: str, ecs_info: Dict, rds_info: Dict) -> str:
    lines = []
    # ECS Status
    if ecs_info.get("status") == "success":
        services = ecs_info.get("services", [])
        if services:
            total = len(services)
            fully_running = sum(1 for s in services if s["desired_count"] > 0 and s["running_count"] == s["desired_count"])
            fully_stopped = sum(1 for s in services if s["desired_count"] == 0 and s["running_count"] == 0)
            
            if fully_running == total:
                lines.append("✅ <b>Services:</b> All running")
            elif fully_stopped == total:
                lines.append("❌ <b>Services:</b> All stopped")
            else:
                lines.append(f"⚠️ <b>Services:</b> {fully_running}/{total} fully running, {fully_stopped}/{total} stopped")
            
            for svc in services:
                name, running, desired, pending = svc["name"], svc["running_count"], svc["desired_count"], svc.get("pending_count", 0)
                if running == desired and desired > 0: lines.append(f"  ✅ {name}: {running} running")
                elif running == desired and desired == 0: lines.append(f"  ❌ {name}: stopped")
                elif pending > 0: lines.append(f"  ⏳ {name}: {running} running, {pending} starting")
                else: lines.append(f"  ⚠️ {name}: {running}/{desired} (transitioning)")
        else:
            lines.append("⚠️ <b>Services:</b> No services found")
    else:
        lines.append(f"❌ <b>Services:</b> {ecs_info.get('message', 'Error')}")
    
    # RDS Status
    if rds_info.get("status") == "success":
        state = rds_info.get("state", "unknown").lower()
        if state == "available": lines.append("✅ <b>Database:</b> Online and ready")
        elif state == "stopped": lines.append("❌ <b>Database:</b> Offline")
        elif "starting" in state or "creating" in state: lines.append("⏳ <b>Database:</b> Starting...")
        elif "stopping" in state: lines.append("⏳ <b>Database:</b> Stopping...")
        else: lines.append(f"⚠️ <b>Database:</b> {state}")
    else:
        lines.append(f"❌ <b>Database:</b> {rds_info.get('message', 'Error')}")
    
    return "\n".join(lines)

def handle_callback(callback_query: dict) -> None:
    cb_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    user_id = str(callback_query["from"]["id"])
    username = callback_query["from"].get("username", "")
    data = callback_query.get("data", "")
    
    if not is_user_authorized(user_id):
        answer_callback(cb_id, "⛔ Unauthorized")
        return
    
    parts = data.split(":")
    if parts[0] == "action":
        action = parts[1]
        if action == "menu":
            edit_message(chat_id, message_id, "👋 <b>Production Control</b>", build_main_menu_keyboard(user_id))
        elif action == "help":
            edit_message(chat_id, message_id, format_help_response(), build_main_menu_keyboard(user_id))
        elif action == "audit":
            audit_text = get_recent_audit(user_id)
            back_kb = {"inline_keyboard": [[{"text": "🎛️ Menu", "callback_data": "action:menu"}]]}
            edit_message(chat_id, message_id, audit_text, back_kb)
        answer_callback(cb_id)
        return
    
    if parts[0] == "exec":
        action, env_name = parts[1], parts[2]
        if env_name not in ENVIRONMENT_MAP or not can_access_env(user_id, env_name):
            answer_callback(cb_id, f"⛔ Unauthorized environment access")
            return
        
        answer_callback(cb_id, f"⏳ Executing {action}...")
        edit_message(chat_id, message_id, f"⏳ Executing <b>{action}</b>...")
        
        env_config = ENVIRONMENT_MAP.get(env_name, {})
        ecs_cluster, rds_instance = env_config.get("ecs_cluster", ""), env_config.get("rds_instances", "")
        
        try:
            if action == "start":
                results = orchestrate_start(ecs_cluster, rds_instance)
                text = format_orchestration_result("start", results)
            elif action == "stop":
                results = orchestrate_stop(ecs_cluster, rds_instance)
                text = format_orchestration_result("stop", results)
            elif action == "status":
                text = format_status_response(env_name, describe_ecs_cluster(ecs_cluster), describe_rds_instance(rds_instance))
            log_audit(user_id, username, action, env_name, f"{ecs_cluster}/{rds_instance}", "success")
        except Exception as e:
            text = format_error(f"Failed: {str(e)}")
            log_audit(user_id, username, action, env_name, "", "error", str(e))
        
        back_kb = {"inline_keyboard": [[{"text": "🎛️ Menu", "callback_data": "action:menu"}]]}
        edit_message(chat_id, message_id, text, back_kb)

def handle_command(chat_id: int, text: str, user_id: str, username: str) -> None:
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower().split("@")[0]
    
    if command in ("/help", "/start", "/menu"):
        send_message(chat_id, format_help_response(), build_main_menu_keyboard(user_id))
        return
    if command == "/audit":
        send_message(chat_id, get_recent_audit(user_id))
        return
    
    action_map = {"/start": "start", "/stop": "stop", "/status": "status"}
    if command not in action_map:
        send_message(chat_id, format_help_response(), build_main_menu_keyboard(user_id))
        return
    
    action, env_name = action_map[command], "prod"
    if env_name not in ENVIRONMENT_MAP or not can_access_env(user_id, env_name):
        send_message(chat_id, "❌ <b>Error</b>\n\nUnauthorized or unconfigured environment")
        return
    
    env_config = ENVIRONMENT_MAP[env_name]
    ecs_cluster, rds_instance = env_config.get("ecs_cluster", ""), env_config.get("rds_instances", "")
    
    try:
        if action == "start": text = format_orchestration_result("start", orchestrate_start(ecs_cluster, rds_instance))
        elif action == "stop": text = format_orchestration_result("stop", orchestrate_stop(ecs_cluster, rds_instance))
        elif action == "status": text = format_status_response(env_name, describe_ecs_cluster(ecs_cluster), describe_rds_instance(rds_instance))
        
        send_message(chat_id, text, {"inline_keyboard": [[{"text": "🎛️ Menu", "callback_data": "action:menu"}]]})
        log_audit(user_id, username, action, env_name, f"{ecs_cluster}/{rds_instance}", "success")
    except Exception as e:
        send_message(chat_id, f"❌ <b>Error</b>\n\n{str(e)[:100]}")
        log_audit(user_id, username, action, env_name, "", "error", str(e))

def lambda_handler(event, context):
    global LAMBDA_ARN
    if not LAMBDA_ARN and context: LAMBDA_ARN = getattr(context, "invoked_function_arn", "")
    
    ok_response = {"statusCode": 200, "body": json.dumps({"ok": True})}
    
    try:
        if WEBHOOK_SECRET and event.get("headers", {}).get("x-telegram-bot-api-secret-token", "") != WEBHOOK_SECRET:
            return ok_response
        
        body = json.loads(event.get("body", "")) if isinstance(event.get("body"), str) else event.get("body", {})
        
        if "callback_query" in body:
            handle_callback(body["callback_query"])
            return ok_response
        
        message = body.get("message")
        if not message or not message.get("text"): return ok_response
        
        user_id = str(message["from"]["id"])
        if not is_user_authorized(user_id):
            send_message(message["chat"]["id"], format_error("You are not authorized."))
            return ok_response
        
        handle_command(message["chat"]["id"], message["text"].strip(), user_id, message["from"].get("username", ""))
    except Exception as e:
        logger.error("Unhandled error: %s", str(e), exc_info=True)
    
    return ok_response

