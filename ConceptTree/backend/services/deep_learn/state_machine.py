from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from models_deep_learn import DeepLearnCommand, DeepLearnState, TeachingMode

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    next_state: DeepLearnState
    action: Literal[
        "teach", "wait_user", "emit_questions",
        "assess_per_question", "show_commands",
        "check_readiness", "show_test_confirm",
        "generate_test_questions", "emit_next_test_q",
        "final_judge", "generate_note", "show_fail_options",
        "abandon_and_restart",
    ]
    teach_mode: Optional[TeachingMode] = None
    advance_concept: bool = False
    mark_skipped: bool = False


def decide_on_init() -> Decision:
    return Decision(next_state="TEACHING", action="teach", teach_mode="normal")


def decide_on_user_message(
    state: DeepLearnState,
    wrong_count: int,
    is_test_phase: bool,
) -> Decision:
    if state == "QUESTIONING":
        return Decision(next_state="EVALUATING", action="assess_per_question")
    if state == "TESTING":
        return Decision(next_state="EVALUATING_TEST", action="assess_per_question")
    logger.warning("decide_on_user_message called in unexpected state: %s", state)
    return Decision(next_state=state, action="wait_user")


def decide_on_assessment_done(
    state: DeepLearnState,
    is_correct: bool,
    new_wrong_count: int,
    test_current_index: int,
    test_total: int = 3,
    all_concepts_done: bool = False,
) -> Decision:
    if state == "EVALUATING":
        if is_correct:
            return Decision(next_state="AWAITING_COMMAND", action="show_commands")
        if new_wrong_count >= 2:
            return Decision(next_state="TEACHING", action="teach", teach_mode="probe_stuck")
        return Decision(next_state="AWAITING_COMMAND", action="show_commands")

    if state == "EVALUATING_TEST":
        if test_current_index < test_total - 1:
            return Decision(next_state="TESTING", action="emit_next_test_q")
        return Decision(next_state="TESTING", action="final_judge")

    logger.warning("decide_on_assessment_done called in unexpected state: %s", state)
    return Decision(next_state=state, action="wait_user")


def decide_on_readiness_done(ready_for_test: bool) -> Decision:
    if ready_for_test:
        return Decision(next_state="CONFIRMING_TEST", action="show_test_confirm")
    return Decision(next_state="TEACHING", action="teach", teach_mode="review_weak")


def decide_on_command(
    state: DeepLearnState,
    command: DeepLearnCommand,
    current_concept_index: int,
    what_list_len: int,
    all_concepts_done: bool,
) -> Decision:
    if command == "restart":
        return Decision(next_state="INITIALIZING", action="abandon_and_restart")

    has_next = current_concept_index + 1 < what_list_len

    if state == "AWAITING_COMMAND":
        if command == "continue":
            if has_next:
                return Decision(
                    next_state="TEACHING", action="teach",
                    teach_mode="normal", advance_concept=True,
                )
            return Decision(next_state="AI_ASSESSING_READINESS", action="check_readiness")

        if command == "expand":
            return Decision(next_state="TEACHING", action="teach", teach_mode="expand")

        if command == "skip":
            if has_next:
                return Decision(
                    next_state="TEACHING", action="teach",
                    teach_mode="normal", advance_concept=True, mark_skipped=True,
                )
            return Decision(
                next_state="AI_ASSESSING_READINESS", action="check_readiness",
                mark_skipped=True,
            )

        if command == "reteach":
            return Decision(next_state="TEACHING", action="teach", teach_mode="reteach")

    if state == "CONFIRMING_TEST":
        if command == "confirm_test":
            return Decision(next_state="TESTING", action="generate_test_questions")
        if command == "not_ready":
            return Decision(next_state="TEACHING", action="teach", teach_mode="review_weak")

    if state == "CHOOSING_AFTER_FAIL":
        if command == "not_ready":
            return Decision(next_state="TEACHING", action="teach", teach_mode="review_weak")

    logger.warning("decide_on_command: unhandled (state=%s, command=%s)", state, command)
    return Decision(next_state=state, action="wait_user")


def decide_on_final_judge(passed: bool) -> Decision:
    if passed:
        return Decision(next_state="GENERATING_NOTE", action="generate_note")
    return Decision(next_state="CHOOSING_AFTER_FAIL", action="show_fail_options")
