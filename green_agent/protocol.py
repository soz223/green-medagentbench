from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field


# ---------- Purple Agent -> Green Agent ----------

class ToolCallAction(BaseModel):
    """让紫色 Agent 调用一个工具的动作。"""

    action: Literal["call_tool"] = "call_tool"
    tool_name: str = Field(..., description="要调用的工具名，比如 get_patient")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="传给工具的参数，必须是一个 JSON 对象",
    )


class FinishAction(BaseModel):
    """紫色 Agent 表示这一局结束，并给出最终总结。"""

    action: Literal["finish"] = "finish"
    final_summary: str = Field(
        ...,
        description="本局任务的最终总结、诊断、处理方案等",
    )


AgentAction = Union[ToolCallAction, FinishAction]


# ---------- Green Agent -> Purple Agent ----------

class ToolSpec(BaseModel):
    """向紫色 Agent 公布有哪些工具可以用。"""

    name: str
    description: str


class Observation(BaseModel):
    """
    Green Agent 返回给紫色 Agent 的“环境观察”。
    以后会作为 prompt 的一部分发给紫色 Agent。
    """

    task_id: str
    task_description: str

    step: int
    max_steps: int

    available_tools: List[ToolSpec]

    # 上一步调用的信息（第一步时为 None）
    last_tool_call: Optional[ToolCallAction] = None
    last_tool_result_brief: Optional[str] = None

    # 是否已经结束（由 Green Agent 内部维护）
    done: bool = False


# ---------- 文本 <-> JSON 的简单帮助函数 ----------

import json


def parse_action_from_text(text: str) -> AgentAction:
    """
    从 LLM 返回的文本中解析 AgentAction。
    要求 LLM 只输出一个 JSON 对象。
    """
    text = text.strip()
    # 有些模型会把 JSON 包在 ```json ``` 代码块里，简单做个裁剪
    if text.startswith("```"):
        # 去掉 ```json 或 ``` 开头
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]

    data = json.loads(text)
    if data.get("action") == "call_tool":
        return ToolCallAction.parse_obj(data)
    elif data.get("action") == "finish":
        return FinishAction.parse_obj(data)
    else:
        raise ValueError(f"Unknown action type in JSON: {data.get('action')}")


def observation_to_json_str(obs: Observation) -> str:
    """
    把 Observation 转成格式化 JSON 字符串，方便直接塞进 prompt/返回给平台。
    """
    return obs.json(indent=2, ensure_ascii=False)
