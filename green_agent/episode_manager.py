from __future__ import annotations

import json
import re
from typing import Tuple, Dict, Any, Optional

from green_agent.protocol import (
    Observation,
    ToolSpec,
    ToolCallAction,
    FinishAction,
    AgentAction,
)
from green_agent.medagent_env_adapter import MedAgentEnvAdapter
from green_agent.task_loader import MedAgentTaskLoader, MedAgentTask

# Module-level task loader - loads tasks once and reuses across episodes
_task_loader: Optional[MedAgentTaskLoader] = None


def _get_task_loader() -> MedAgentTaskLoader:
    """Get or initialize the global task loader."""
    global _task_loader
    if _task_loader is None:
        _task_loader = MedAgentTaskLoader()
    return _task_loader


# Import refsol evaluation module
try:
    from src.server.tasks.medagentbench.eval import eval as refsol_eval
    REFSOL_AVAILABLE = True
except ImportError:
    REFSOL_AVAILABLE = False
    print("[Warning] Could not import refsol evaluation module. Scoring will not be available.")


class HistoryItem:
    """
    Simple history item compatible with MedAgentBench's ChatHistoryItem.

    Represents a single message in the interaction history between
    the agent and the environment.
    """
    def __init__(self, role: str, content: str):
        """
        Initialize a history item.

        Args:
            role: Either "agent" or "user"
            content: The message content
        """
        self.role = role
        self.content = content

    def __repr__(self):
        return f"HistoryItem(role={self.role}, content={self.content[:50]}...)"


class EpisodeManager:
    """
    管理一局交互（episode）的控制器：最小可用版本（Option A）。

    现在它做的事情：
    - reset(): 生成一个固定的“占位任务”（后面会换成 MedAgentBench 真任务）
    - step(action): 
        * 如果是 call_tool -> 调 FHIR 工具 -> 返回新的 Observation
        * 如果是 finish -> 标记 done=True，给一个固定 reward=0.0（以后接 refsol）
    """

    def __init__(self, env: MedAgentEnvAdapter, max_steps: int = 8):
        self.env = env
        self.max_steps = max_steps

        # Task-related attributes (initialized in reset())
        self.task_id: str = ""
        self.task_description: str = ""
        self.patient_id: str = ""  # MRN of the patient for this task
        self.gold_answer: list = []  # Gold answer for scoring
        self.task_raw_data: dict = {}  # Original task dict for refsol scoring

        # Episode state
        self.current_step: int = 0
        self.done: bool = False
        self.last_tool_call: Optional[ToolCallAction] = None
        self.last_tool_result_brief: Optional[str] = None

        # Interaction history for refsol (Stage 4)
        self.history: list = []  # List[HistoryItem]

    # ---------- 公共接口 ----------

    def reset(
        self,
        task_id: Optional[str] = None,
        task_description: Optional[str] = None,
    ) -> Observation:
        """
        重置一局任务，从 MedAgentBench 真任务池中 sample 一个任务。

        - task_id: (Optional) 如果提供，会尝试加载指定任务；否则随机采样
        - task_description: (Optional) 如果提供，会覆盖任务描述（通常用于测试）
        """

        # Load or sample a task from MedAgentBench
        loader = _get_task_loader()

        if task_id is not None:
            # Try to load specific task by ID
            sampled_task = loader.get_task_by_id(task_id)
            if sampled_task is None:
                raise ValueError(f"Task with ID '{task_id}' not found in task pool")
        else:
            # Sample a random task
            sampled_task = loader.sample_random_task()

        # Set task attributes from sampled task
        self.task_id = sampled_task.task_id
        self.patient_id = sampled_task.patient_id
        self.gold_answer = sampled_task.gold_answer
        self.task_raw_data = sampled_task.raw_data

        # Build task description with patient MRN and context
        if task_description is not None:
            # Allow override for testing
            self.task_description = task_description
        else:
            # Build rich description from task data
            desc_parts = [f"Patient MRN: {sampled_task.patient_id}"]

            if sampled_task.context:
                desc_parts.append(f"Context: {sampled_task.context}")

            desc_parts.append(f"Task: {sampled_task.instruction}")

            self.task_description = "\n".join(desc_parts)

        self.current_step = 0
        self.done = False
        self.last_tool_call = None
        self.last_tool_result_brief = None

        # Clear interaction history for new episode
        self.history = []

        available_tools = self.env.list_available_tools()

        return Observation(
            task_id=self.task_id,
            task_description=self.task_description,
            step=self.current_step,
            max_steps=self.max_steps,
            available_tools=available_tools,
            last_tool_call=None,
            last_tool_result_brief=None,
            done=False,
        )

    def step(self, action: AgentAction) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """
        接受紫色 Agent 的一个动作，返回：
        - observation: 下一步给紫色 Agent 的观察
        - reward: 本步 reward（现在简单设为 0.0，结束时也先不区分成败）
        - done: 是否本局结束
        - info: 额外调试信息

        TODO(Polish-2): 后续把 reward 和 done 与 refsol 真正衔接。
        """
        if self.done:
            obs = self._build_observation()
            return obs, 0.0, True, {"reason": "episode_already_done"}

        self.current_step += 1

        # Tool call - execute tool and record in history
        if isinstance(action, ToolCallAction):
            # Execute the tool
            result_text = self.env.handle_tool_call(action)
            self.last_tool_call = action
            self.last_tool_result_brief = result_text

            # Record tool call in history (agent action)
            tool_call_msg = self._format_tool_call_for_history(action)
            self.history.append(HistoryItem(role="agent", content=tool_call_msg))

            # Record tool result in history (environment response)
            # Special handling for POST tools - refsol expects specific response format
            if action.tool_name == "post_fhir_resource":
                # For POST, refsol expects: "POST request accepted and executed successfully"
                # regardless of the actual result message
                self.history.append(HistoryItem(role="user", content="POST request accepted and executed successfully"))
            else:
                # For other tools, use the actual result (truncated if too long)
                result_brief = result_text[:500] if len(result_text) > 500 else result_text
                self.history.append(HistoryItem(role="user", content=result_brief))

            if self.current_step >= self.max_steps:
                self.done = True
                obs = self._build_observation()
                return obs, 0.0, True, {"reason": "max_steps_reached"}

            obs = self._build_observation()
            return obs, 0.0, False, {}

        # Finish - record in history and evaluate the agent's answer
        if isinstance(action, FinishAction):
            self.done = True

            # Record finish action in history (agent message)
            # Format as FINISH([answer]) to match MedAgentBench convention
            finish_msg = f"FINISH: {action.final_summary}"
            self.history.append(HistoryItem(role="agent", content=finish_msg))

            # Evaluate the final answer using refsol (passes history)
            reward, evaluation = self._evaluate_answer(action.final_summary)

            obs = self._build_observation()
            info = {
                "final_summary": action.final_summary,
                "evaluation": evaluation,
                "task_id": self.task_id,
                "patient_id": self.patient_id,
            }

            return obs, reward, True, info

        # 理论上不会走到这里
        obs = self._build_observation()
        return obs, 0.0, False, {"warning": f"unknown action type: {type(action)}"}

    # ---------- 内部辅助 ----------

    def _build_observation(self) -> Observation:
        available_tools = self.env.list_available_tools()
        return Observation(
            task_id=self.task_id,
            task_description=self.task_description,
            step=self.current_step,
            max_steps=self.max_steps,
            available_tools=available_tools,
            last_tool_call=self.last_tool_call,
            last_tool_result_brief=self.last_tool_result_brief,
            done=self.done,
        )

    def _format_tool_call_for_history(self, action: ToolCallAction) -> str:
        """
        Format a tool call action as a message for history.

        Creates a readable representation of the tool call that resembles
        MedAgentBench's GET/POST format for compatibility with refsol.

        For POST tools (post_fhir_resource), formats as:
            POST {url}
            {json_payload}

        For other tools, formats as GET-style request.

        Args:
            action: The tool call action to format

        Returns:
            Formatted string representing the tool call
        """
        # Special handling for POST tools - match refsol's expected format
        if action.tool_name == "post_fhir_resource":
            args = action.arguments or {}
            resource_type = args.get("resource_type", "Unknown")
            payload = args.get("payload", {})

            # Build URL: {fhir_base_url}/{resource_type}
            url = f"{self.env.fhir_base_url}/{resource_type}"

            # Format as: POST {url}\n{json_payload}
            # This matches what refsol.extract_posts() expects
            payload_json = json.dumps(payload, indent=None)
            return f"POST {url}\n{payload_json}"

        # For other tools, format as GET-like request
        # This helps refsol understand it's not a POST (which some tasks prohibit)
        args_str = json.dumps(action.arguments) if action.arguments else "{}"
        return f"GET {action.tool_name} with arguments: {args_str}"

    def _evaluate_answer(self, final_summary: str) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate the agent's final answer using MedAgentBench refsol.

        This method extracts the answer from the agent's final_summary,
        creates a mock results object, and calls the refsol eval function
        to determine correctness.

        Args:
            final_summary: The agent's final answer text

        Returns:
            Tuple of (reward, evaluation_dict) where:
            - reward: 1.0 if correct, 0.0 if incorrect
            - evaluation_dict: Contains 'correct', 'extracted_answer', 'error' etc.
        """
        evaluation = {
            "correct": False,
            "extracted_answer": None,
            "error": None,
        }

        # Check if refsol is available
        if not REFSOL_AVAILABLE:
            evaluation["error"] = "refsol_not_available"
            return 0.0, evaluation

        # Check if we have task data
        if not self.task_raw_data:
            evaluation["error"] = "no_task_data"
            return 0.0, evaluation

        try:
            # Step 1: Extract answer from final_summary
            # The original MedAgentBench expects format: FINISH(["answer"])
            # We need to extract JSON array from the summary
            extracted_answer = self._extract_answer_from_summary(final_summary)
            evaluation["extracted_answer"] = extracted_answer

            if extracted_answer is None:
                evaluation["error"] = "failed_to_extract_answer"
                return 0.0, evaluation

            # Step 2: Create a mock results object that refsol expects
            # refsol expects: results.result (JSON string) and results.history (list)
            class MockResults:
                def __init__(self, result_str, history_items):
                    self.result = result_str  # JSON string like '["answer"]'
                    self.history = history_items  # List of HistoryItem objects

            # Convert extracted answer to JSON string
            result_json = json.dumps(extracted_answer)

            # Pass the actual interaction history (Stage 4)
            mock_results = MockResults(result_json, self.history)

            # Step 3: Call refsol eval function
            # eval(case_data, results, fhir_api_base)
            fhir_base_url = self.env.fhir_base_url
            is_correct = refsol_eval(self.task_raw_data, mock_results, fhir_base_url)

            evaluation["correct"] = bool(is_correct)
            reward = 1.0 if is_correct else 0.0

            return reward, evaluation

        except Exception as e:
            evaluation["error"] = f"evaluation_exception: {str(e)}"
            return 0.0, evaluation

    def _extract_answer_from_summary(self, text: str) -> Optional[Any]:
        """
        Extract answer from agent's final summary text.

        Tries multiple strategies:
        1. Look for JSON array like ["answer"] or [value]
        2. Look for FINISH([...]) format
        3. Try to parse entire text as JSON
        4. Extract single quoted/unquoted value

        Args:
            text: The final summary text

        Returns:
            Extracted answer (typically a list), or None if extraction fails
        """
        if not text:
            return None

        # Strategy 1: Find JSON array pattern [...]
        # Look for patterns like ["answer"], [123], ["a", "b"]
        json_pattern = r'\[(?:[^\[\]]*|\[[^\[\]]*\])*\]'
        matches = re.findall(json_pattern, text)

        for match in matches:
            try:
                parsed = json.loads(match)
                # Prefer lists (which is what refsol expects)
                if isinstance(parsed, list):
                    return parsed
            except:
                continue

        # Strategy 2: Look for FINISH(...) format
        finish_pattern = r'FINISH\s*\((.*?)\)'
        finish_match = re.search(finish_pattern, text, re.IGNORECASE)
        if finish_match:
            try:
                content = finish_match.group(1)
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [parsed]  # Wrap in list
            except:
                pass

        # Strategy 3: Try to parse entire text as JSON
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return parsed
            else:
                return [parsed]
        except:
            pass

        # Strategy 4: Extract probable answer strings/numbers
        # Look for patterns like: "The answer is X", "MRN: X", etc.
        # Common patterns in medical tasks
        patterns = [
            r'(?:answer|result|mrn|value)(?:\s+is)?:?\s*["\']?([A-Z0-9][A-Z0-9\-]+)',  # MRN/alphanumeric
            r'\b([S][0-9]{7})\b',  # MRN pattern like S1234567
            r'\b([0-9]+(?:\.[0-9]+)?)\b',  # Numeric answers
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Clean up the match (remove trailing punctuation)
                answer = match.group(1).rstrip('.,;:!?')
                return [answer]

        # Failed to extract
        return None
