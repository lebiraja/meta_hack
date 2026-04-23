from env.graders.task_easy import grade as grade_easy
from env.graders.task_medium import grade as grade_medium
from env.graders.task_hard import grade as grade_hard
from env.graders.task_nightmare import grade as grade_nightmare
from env.graders.task_hierarchy_easy import grade as grade_hierarchy_easy
from env.graders.task_hierarchy_medium import grade as grade_hierarchy_medium
from env.graders.task_hierarchy_hard import grade as grade_hierarchy_hard

GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    "nightmare": grade_nightmare,
    "hierarchy_easy": grade_hierarchy_easy,
    "hierarchy_medium": grade_hierarchy_medium,
    "hierarchy_hard": grade_hierarchy_hard,
}


def grade(task: str, session_state: dict) -> float:
    grader = GRADERS.get(task)
    if not grader:
        raise ValueError(f"No grader for task '{task}'")
    return grader(session_state)
