from env.graders.task_easy import grade as grade_easy
from env.graders.task_medium import grade as grade_medium
from env.graders.task_hard import grade as grade_hard
from env.graders.task_nightmare import grade as grade_nightmare
from env.graders.task_hierarchy_easy import grade as grade_hierarchy_easy
from env.graders.task_hierarchy_medium import grade as grade_hierarchy_medium
from env.graders.task_hierarchy_hard import grade as grade_hierarchy_hard
from env.graders.task_curriculum_basic import grade as grade_curriculum_basic
from env.graders.task_curriculum_supervisor import grade as grade_curriculum_supervisor
from env.graders.task_curriculum_full_hierarchy import grade as grade_curriculum_full_hierarchy
from env.graders.task_curriculum_nightmare import grade as grade_curriculum_nightmare
from env.graders.task_multi_domain import grade as grade_multi_domain

GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    "nightmare": grade_nightmare,
    "hierarchy_easy": grade_hierarchy_easy,
    "hierarchy_medium": grade_hierarchy_medium,
    "hierarchy_hard": grade_hierarchy_hard,
    "curriculum_basic": grade_curriculum_basic,
    "curriculum_supervisor": grade_curriculum_supervisor,
    "curriculum_full_hierarchy": grade_curriculum_full_hierarchy,
    "curriculum_nightmare": grade_curriculum_nightmare,
    "multi_domain": grade_multi_domain,
}


def grade(task: str, session_state: dict) -> float:
    grader = GRADERS.get(task)
    if not grader:
        raise ValueError(f"No grader for task '{task}'")
    return grader(session_state)
