"""Unit tests for deep_learn state machine — no DB, no LLM."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.deep_learn.state_machine import (
    Decision,
    decide_on_init,
    decide_on_user_message,
    decide_on_assessment_done,
    decide_on_readiness_done,
    decide_on_command,
    decide_on_final_judge,
)


# ── decide_on_init ──────────────────────────────────────────────────────────


def test_init_starts_teaching():
    d = decide_on_init()
    assert d.next_state == "TEACHING"
    assert d.action == "teach"
    assert d.teach_mode == "normal"


# ── decide_on_user_message ──────────────────────────────────────────────────


def test_user_message_in_questioning_goes_evaluating():
    d = decide_on_user_message("QUESTIONING", 0, False)
    assert d.next_state == "EVALUATING"
    assert d.action == "assess_per_question"


def test_user_message_in_testing_goes_evaluating_test():
    d = decide_on_user_message("TESTING", 0, True)
    assert d.next_state == "EVALUATING_TEST"
    assert d.action == "assess_per_question"


def test_user_message_unexpected_state_returns_wait():
    d = decide_on_user_message("TEACHING", 0, False)
    assert d.next_state == "TEACHING"
    assert d.action == "wait_user"


# ── decide_on_assessment_done ───────────────────────────────────────────────


def test_assessment_correct_goes_awaiting_command():
    d = decide_on_assessment_done("EVALUATING", True, 0, 0)
    assert d.next_state == "AWAITING_COMMAND"
    assert d.action == "show_commands"


def test_assessment_wrong_once_goes_awaiting_command():
    d = decide_on_assessment_done("EVALUATING", False, 1, 0)
    assert d.next_state == "AWAITING_COMMAND"
    assert d.action == "show_commands"


def test_assessment_wrong_twice_triggers_probe_stuck():
    d = decide_on_assessment_done("EVALUATING", False, 2, 0)
    assert d.next_state == "TEACHING"
    assert d.action == "teach"
    assert d.teach_mode == "probe_stuck"


def test_evaluating_test_not_last_advances():
    d = decide_on_assessment_done("EVALUATING_TEST", True, 0, 0, test_total=3)
    assert d.next_state == "TESTING"
    assert d.action == "emit_next_test_q"


def test_evaluating_test_last_goes_final_judge():
    d = decide_on_assessment_done("EVALUATING_TEST", True, 0, 2, test_total=3)
    assert d.next_state == "TESTING"
    assert d.action == "final_judge"


# ── decide_on_readiness_done ────────────────────────────────────────────────


def test_readiness_ready_goes_confirming_test():
    d = decide_on_readiness_done(True)
    assert d.next_state == "CONFIRMING_TEST"
    assert d.action == "show_test_confirm"


def test_readiness_not_ready_goes_review_weak():
    d = decide_on_readiness_done(False)
    assert d.next_state == "TEACHING"
    assert d.teach_mode == "review_weak"


# ── decide_on_command ───────────────────────────────────────────────────────


def test_cmd_continue_has_next():
    d = decide_on_command("AWAITING_COMMAND", "continue", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.advance_concept is True
    assert d.teach_mode == "normal"


def test_cmd_continue_no_next_checks_readiness():
    d = decide_on_command("AWAITING_COMMAND", "continue", 2, 3, True)
    assert d.next_state == "AI_ASSESSING_READINESS"
    assert d.action == "check_readiness"


def test_cmd_expand():
    d = decide_on_command("AWAITING_COMMAND", "expand", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.teach_mode == "expand"


def test_cmd_skip_has_next():
    d = decide_on_command("AWAITING_COMMAND", "skip", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.mark_skipped is True
    assert d.advance_concept is True


def test_cmd_skip_no_next():
    d = decide_on_command("AWAITING_COMMAND", "skip", 2, 3, True)
    assert d.next_state == "AI_ASSESSING_READINESS"
    assert d.mark_skipped is True


def test_cmd_reteach():
    d = decide_on_command("AWAITING_COMMAND", "reteach", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.teach_mode == "reteach"


def test_cmd_confirm_test():
    d = decide_on_command("CONFIRMING_TEST", "confirm_test", 0, 3, False)
    assert d.next_state == "TESTING"
    assert d.action == "generate_test_questions"


def test_cmd_not_ready_from_confirming():
    d = decide_on_command("CONFIRMING_TEST", "not_ready", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.teach_mode == "review_weak"


def test_cmd_not_ready_from_choosing_after_fail():
    d = decide_on_command("CHOOSING_AFTER_FAIL", "not_ready", 0, 3, False)
    assert d.next_state == "TEACHING"
    assert d.teach_mode == "review_weak"


def test_cmd_restart_any_state():
    for state in ["TEACHING", "QUESTIONING", "AWAITING_COMMAND", "CHOOSING_AFTER_FAIL"]:
        d = decide_on_command(state, "restart", 0, 3, False)
        assert d.next_state == "INITIALIZING"
        assert d.action == "abandon_and_restart"


# ── decide_on_final_judge ────────────────────────────────────────────────────


def test_final_judge_passed():
    d = decide_on_final_judge(True)
    assert d.next_state == "GENERATING_NOTE"
    assert d.action == "generate_note"


def test_final_judge_failed():
    d = decide_on_final_judge(False)
    assert d.next_state == "CHOOSING_AFTER_FAIL"
    assert d.action == "show_fail_options"
