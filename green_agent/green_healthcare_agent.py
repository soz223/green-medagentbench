from __future__ import annotations

from typing import Dict, Any, Tuple

from green_agent.protocol import (
    Observation,
    AgentAction,
    parse_action_from_text,
    observation_to_json_str,
)
from green_agent.medagent_env_adapter import MedAgentEnvAdapter
from green_agent.episode_manager import EpisodeManager


SYSTEM_INSTRUCTION = """
你是一个医疗评估环境的"裁判代理"（Green Agent 的被测方是紫色 Agent）。
你不会自己做诊疗决策，只负责：

1. 把当前任务、可用工具、上一步工具结果等信息，用 JSON 形式告诉紫色 Agent；
2. 接收紫色 Agent 输出的 JSON（调用工具或结束任务），并执行相应操作。

紫色 Agent 必须严格遵守以下输出格式之一：

1）调用工具：action="call_tool", tool_name=工具名, arguments=参数对象
2）结束任务：action="finish", final_summary=最终总结

禁止输出任何额外文字，禁止输出多个 JSON 对象。
"""


class GreenHealthcareAgent:
    """
    对外暴露的“绿色医疗 Agent”壳子。

    外部只需要调用：
    - reset() -> str（发给紫色 Agent 的提示文本）
    - step(text_from_purple: str) -> (str, float, bool, dict)
      * 输入：紫色 Agent 的文本（必须只包含一个 JSON）
      * 输出：
          - new_prompt: 下一步提示文本（Observation + 规则）
          - reward: 本步奖励（目前都是 0.0，finish 时也先用 0.0 占位）
          - done: 是否结束
          - info: 额外信息（例如最终总结、评估结果等）
    """

    def __init__(self, fhir_base_url: str = "http://localhost:8080/fhir", max_steps: int = 8):
        self.env = MedAgentEnvAdapter(fhir_base_url=fhir_base_url)
        self.episode = EpisodeManager(self.env, max_steps=max_steps)

    # ---------- 对外接口 ----------

    def reset(self) -> str:
        """
        开启一局新任务，返回给紫色 Agent 的“首条提示”。

        返回的是一个字符串，通常会拼在 system / user prompt 里。
        结构约定：
        - 先给一段系统说明（SYSTEM_INSTRUCTION）
        - 然后附上当前 Observation 的 JSON
        """
        obs = self.episode.reset()
        return self._build_prompt_from_observation(obs)

    def step(self, text_from_purple: str) -> Tuple[str, float, bool, Dict[str, Any]]:
        """
        外部调用：
        - text_from_purple: 紫色 Agent 的输出文本（应该只包含一个 JSON 对象）
        - 返回：
            * new_prompt: 下一步提示（Observation + 规则）
            * reward: 本步 reward（当前版本简单统一返回 0.0）
            * done: episode 是否结束
            * info: 额外信息（例如最终总结、内部调试字段等）
        """
        # 1. 解析 JSON -> AgentAction
        try:
            action: AgentAction = parse_action_from_text(text_from_purple)
        except Exception as e:
            # 解析失败：给紫色 Agent 一个明确的错误提示，不结束 episode
            obs = self._get_current_observation()
            error_msg = f"解析你的 JSON 失败：{e}。请严格按照约定只输出一个 JSON 对象。"
            # 在提示里加入错误说明
            prompt = self._build_prompt_from_observation(obs, extra_system_note=error_msg)
            return prompt, 0.0, False, {"error": str(e)}

        # 2. 把 action 交给 EpisodeManager
        obs, reward, done, info = self.episode.step(action)

        # 3. 把新的 observation 转成下一步提示文本
        prompt = self._build_prompt_from_observation(obs)
        return prompt, reward, done, info

    # ---------- 内部辅助 ----------

    def _get_current_observation(self) -> Observation:
        """
        当前简单实现：重新 build 一下 observation。
        EpisodeManager 的 _build_observation 已经包含所需信息。
        这里我们直接调用一次 step 中使用的内部逻辑比较麻烦，
        因此先通过 reset/step 的结构维护 current_obs 会更优，
        不过在当前最小版本中，我们利用 episode 的内部状态重新构造。
        """
        # 这里其实就是 EpisodeManager._build_observation 的逻辑复制一遍，
        # 为了简单我们直接调用它的私有方法（虽然不太优雅，但先用）。
        return self.episode._build_observation()  # type: ignore

    def _build_prompt_from_observation(
        self,
        obs: Observation,
        extra_system_note: str | None = None,
    ) -> str:
        """
        把 Observation + 规则说明 拼成一段给紫色 Agent 的提示文本。
        以后接到 AgentBeats 时，可以把这段作为 user/system prompt。
        """
        obs_json = observation_to_json_str(obs)

        note = ""
        if extra_system_note:
            note = f"\n\n[系统补充提示]: {extra_system_note}\n"

        prompt = (
            SYSTEM_INSTRUCTION.strip()
            + note
            + "\n\n[当前环境观察 Observation(JSON) ]:\n"
            + obs_json
            + "\n\n请严格按照上面的规则，只输出一个 JSON 对象作为你的动作。"
        )
        return prompt
