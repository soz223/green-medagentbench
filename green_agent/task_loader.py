"""
Task loader for MedAgentBench tasks.
Loads task data from JSON file and provides sampling functionality.
"""
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class MedAgentTask:
    """Represents a single MedAgentBench task."""
    task_id: str
    patient_id: str  # MRN from eval_MRN field
    instruction: str
    context: str
    gold_answer: List[str]  # For future Stage 3 scoring
    raw_data: dict  # Original task dict for scoring with refsol


class MedAgentTaskLoader:
    """
    Loader for MedAgentBench tasks.
    Loads tasks once and provides random sampling.
    """

    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize the task loader.

        Args:
            data_file: Path to the task data JSON file.
                      If None, uses default: data/medagentbench/test_data_v2.json
        """
        if data_file is None:
            # Find repo root (green_agent is one level below repo root)
            repo_root = Path(__file__).resolve().parents[1]
            data_file = repo_root / "data" / "medagentbench" / "test_data_v2.json"

        self.data_file = Path(data_file)
        self.tasks: List[MedAgentTask] = []
        self._load_tasks()

    def _load_tasks(self):
        """Load all tasks from the JSON file."""
        if not self.data_file.exists():
            raise FileNotFoundError(
                f"Task data file not found: {self.data_file}\n"
                f"Please ensure MedAgentBench data is available."
            )

        with open(self.data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Parse each task into MedAgentTask object
        for item in raw_data:
            task = MedAgentTask(
                task_id=item['id'],
                # Some tasks don't have a patient (e.g., "Patient not found" cases)
                patient_id=item.get('eval_MRN', 'UNKNOWN'),
                instruction=item['instruction'],
                context=item.get('context', ''),
                gold_answer=item.get('sol', []),
                raw_data=item  # Store original dict for scoring
            )
            self.tasks.append(task)

        print(f"[TaskLoader] Loaded {len(self.tasks)} tasks from {self.data_file}")

    def sample_random_task(self) -> MedAgentTask:
        """
        Sample a random task from the task pool.

        Returns:
            A randomly selected MedAgentTask
        """
        if not self.tasks:
            raise RuntimeError("No tasks loaded. Cannot sample.")

        return random.choice(self.tasks)

    def get_task_by_id(self, task_id: str) -> Optional[MedAgentTask]:
        """
        Get a specific task by its ID.

        Args:
            task_id: The task ID to retrieve

        Returns:
            The MedAgentTask with the given ID, or None if not found
        """
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def __len__(self) -> int:
        """Return the number of tasks in the pool."""
        return len(self.tasks)
