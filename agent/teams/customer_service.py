# Customer Service Agent – after-sales / emergency specialist
from __future__ import annotations

import hashlib
import re
from typing import Any

from agent.models import AgentName, AgentTask
from agent.teams.base import BaseAgent


class CustomerServiceAgent(BaseAgent):
  name = AgentName.CUSTOMER_SERVICE
  description = "Handles after-sales support, complaints, and travel emergencies."
  _success_label = "Customer service plan generated"
  _failure_label = "Customer service handling failed"

  system_prompt = """You are the Customer Service Agent for TravelMind.

You handle urgent travel support and post-booking issues, such as:
- flight cancellation/delay and rebooking
- hotel check-in disputes
- refund and change requests
- complaints and emergency escalation

Given the incident context, provide:
1. Immediate actions the traveler should take now.
2. A step-by-step handling workflow with clear priorities.
3. Required documents/evidence.
4. Escalation path and expected timeline.

Respond in the user's language.
Be calm, practical, and safety-first."""

  async def _run_tools(
    self, task: AgentTask, context: dict[str, Any],
  ) -> dict[str, Any]:
    """Build structured incident analysis from user task/context."""
    params = task.params or {}
    msg = self._merge_issue_text(task.goal, params, context)

    incident_type = self._detect_incident_type(msg)
    severity = self._detect_severity(msg)
    urgency = self._urgency_from_severity(severity)
    references = self._extract_references(msg)

    actions = self._recommended_actions(incident_type, severity)
    docs = self._required_documents(incident_type)
    escalation = self._escalation_policy(incident_type, severity)

    return {
      "incident_type": incident_type,
      "severity": severity,
      "urgency": urgency,
      "references": references,
      "recommended_actions": actions,
      "required_documents": docs,
      "escalation": escalation,
      "ticket_id": self._make_ticket_id(msg),
    }

  def _build_prompt(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
  ) -> str:
    base = super()._build_prompt(task, context, tool_data)
    return (
      f"{base}\n\n"
      "Please provide a concise incident response plan with: "
      "immediate actions, recovery options, and escalation timeline."
    )

  def _post_process(
    self,
    task: AgentTask,
    context: dict[str, Any],
    tool_data: dict[str, Any],
    response: str,
  ) -> dict[str, Any]:
    """Return both structured plan and LLM response text."""
    return {
      "response": response,
      "tool_data": tool_data,
      "ticket_id": tool_data.get("ticket_id", ""),
      "incident_type": tool_data.get("incident_type", "other"),
      "severity": tool_data.get("severity", "medium"),
      "urgency": tool_data.get("urgency", "normal"),
      "recommended_actions": tool_data.get("recommended_actions", []),
      "required_documents": tool_data.get("required_documents", []),
      "escalation": tool_data.get("escalation", {}),
      "references": tool_data.get("references", {}),
    }

  @staticmethod
  def _merge_issue_text(
    goal: str,
    params: dict[str, Any],
    context: dict[str, Any],
  ) -> str:
    parts = [goal or ""]
    for key in ("issue", "message", "details", "request", "complaint"):
      val = params.get(key)
      if isinstance(val, str) and val.strip():
        parts.append(val.strip())
    state_ctx = context.get("state_context", "")
    if state_ctx:
      parts.append(str(state_ctx)[:500])
    return "\n".join(parts)

  @staticmethod
  def _detect_incident_type(text: str) -> str:
    msg = text.lower()
    if any(k in msg for k in ("取消", "cancel", "航班取消", "酒店取消")):
      return "cancellation"
    if any(k in msg for k in ("延误", "delay", "晚点")):
      return "delay"
    if any(k in msg for k in ("改签", "rebook", "改期", "change flight")):
      return "rebooking"
    if any(k in msg for k in ("退款", "refund", "退费", "退票")):
      return "refund"
    if any(k in msg for k in ("投诉", "complaint", "态度", "服务差")):
      return "complaint"
    if any(k in msg for k in ("行李", "丢失", "lost", "找不到")):
      return "baggage"
    if any(k in msg for k in ("紧急", "emergency", "事故", "受伤", "生病")):
      return "emergency"
    return "other"

  @staticmethod
  def _detect_severity(text: str) -> str:
    msg = text.lower()
    if any(k in msg for k in ("紧急", "emergency", "受伤", "生病", "被困", "今晚")):
      return "critical"
    if any(k in msg for k in ("取消", "cancel", "延误", "delay", "无法入住", "无法登机")):
      return "high"
    if any(k in msg for k in ("投诉", "complaint", "退款", "refund")):
      return "medium"
    return "low"

  @staticmethod
  def _urgency_from_severity(severity: str) -> str:
    return {
      "critical": "immediate",
      "high": "urgent",
      "medium": "normal",
      "low": "low",
    }.get(severity, "normal")

  @staticmethod
  def _extract_references(text: str) -> dict[str, list[str]]:
    # booking ref, order id, and flight number candidates
    order_ids = re.findall(r"(?:订单|order|booking)[\s:#-]*([A-Za-z0-9-]{5,})", text, re.I)
    flight_nos = re.findall(r"\b([A-Z]{2}\d{3,4})\b", text.upper())
    dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    return {
      "order_ids": order_ids[:3],
      "flight_numbers": flight_nos[:3],
      "dates": dates[:3],
    }

  @staticmethod
  def _recommended_actions(incident_type: str, severity: str) -> list[str]:
    common = [
      "先确认订单状态与时间节点，保存系统通知截图。",
      "联系相关供应商（航司/酒店/平台）并记录沟通时间与工单号。",
    ]
    mapping = {
      "cancellation": [
        "优先申请免费改签到最早可行班次或同等级替代方案。",
        "如无可替代行程，立即走全额退款并申请连带损失补偿。",
      ],
      "delay": [
        "确认延误时长是否满足餐食/住宿赔付条件。",
        "若影响后续行程，先锁定备选交通再处理原订单。",
      ],
      "rebooking": [
        "按“同日最短中转、总时长最短”筛选替代班次。",
        "改签前确认差价、退改规则和行李额度是否变化。",
      ],
      "refund": [
        "核对退改条款中的手续费和到账周期。",
        "提交退款后保留申请凭证，超时自动升级人工。",
      ],
      "complaint": [
        "整理客观证据（照片、录音、聊天记录、时间线）。",
        "按平台投诉入口提交，并同步要求明确回复时限。",
      ],
      "baggage": [
        "在机场/车站现场先报备遗失并拿到书面受理单。",
        "补充行李外观、标签号和贵重物品清单。",
      ],
      "emergency": [
        "优先保障人身安全，必要时先联系当地急救和警方。",
        "同时联系领事保护/保险援助，启动紧急协助流程。",
      ],
      "other": ["提供完整事件时间线，便于快速分流到对应团队。"],
    }
    extra = mapping.get(incident_type, mapping["other"])
    if severity == "critical":
      extra = ["将该工单标记为最高优先级并立即人工介入。"] + extra
    return common + extra

  @staticmethod
  def _required_documents(incident_type: str) -> list[str]:
    base = ["订单号", "身份证件/护照", "支付凭证", "问题截图或照片"]
    specific = {
      "cancellation": ["取消通知", "替代方案报价截图"],
      "delay": ["延误证明", "后续行程受影响凭证"],
      "rebooking": ["原客票信息", "目标班次信息"],
      "refund": ["退改规则页面截图", "退款申请记录"],
      "complaint": ["投诉对象信息", "完整沟通记录"],
      "baggage": ["行李牌", "遗失受理单"],
      "emergency": ["医疗/警方证明", "保险保单号"],
    }
    return base + specific.get(incident_type, [])

  @staticmethod
  def _escalation_policy(incident_type: str, severity: str) -> dict[str, Any]:
    if severity == "critical":
      return {
        "required": True,
        "channel": "priority_hotline",
        "target_sla_minutes": 10,
      }
    if incident_type in {"cancellation", "delay", "baggage"}:
      return {
        "required": True,
        "channel": "human_agent",
        "target_sla_minutes": 30,
      }
    return {
      "required": False,
      "channel": "self_service_then_agent",
      "target_sla_minutes": 120,
    }

  @staticmethod
  def _make_ticket_id(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"CS-{digest.upper()}"
