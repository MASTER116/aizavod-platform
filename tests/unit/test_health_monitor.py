"""Unit tests: Health Monitor + DEADMAN kill-switch."""

import pytest
from services.health_monitor import HealthMonitor, AgentStatus


class TestHealthMonitor:
    def setup_method(self):
        self.hm = HealthMonitor(error_threshold=0.3, latency_threshold_ms=5000)

    def test_register_agent(self):
        self.hm.register("test_agent")
        status = self.hm.get_status("test_agent")
        assert status is not None
        assert status["status"] == "healthy"

    def test_record_success(self):
        self.hm.record_call("agent1", 100.0, True)
        status = self.hm.get_status("agent1")
        assert status["total_calls"] == 1
        assert status["total_errors"] == 0

    def test_auto_unhealthy_on_high_error_rate(self):
        # 4 errors out of 10 = 40% > 30% threshold
        for _ in range(6):
            self.hm.record_call("agent1", 100.0, True)
        for _ in range(4):
            self.hm.record_call("agent1", 100.0, False, "test error")
        status = self.hm.get_status("agent1")
        assert status["status"] == "unhealthy"

    def test_kill_switch(self):
        self.hm.register("agent1")
        assert self.hm.can_execute("agent1")
        self.hm.kill("agent1", "manual kill")
        assert not self.hm.can_execute("agent1")
        assert self.hm.is_killed("agent1")

    def test_revive_after_kill(self):
        self.hm.register("agent1")
        self.hm.kill("agent1", "test")
        assert not self.hm.can_execute("agent1")
        self.hm.revive("agent1")
        assert self.hm.can_execute("agent1")
        assert not self.hm.is_killed("agent1")

    def test_summary(self):
        self.hm.record_call("a1", 100.0, True)
        self.hm.record_call("a2", 200.0, True)
        self.hm.kill("a3", "test")
        summary = self.hm.get_summary()
        assert summary["total_agents"] == 3
        assert summary["killed"] == 1
        assert "a3" in summary["killed_agents"]

    def test_unhealthy_blocks_execution(self):
        # Force unhealthy
        for _ in range(10):
            self.hm.record_call("agent1", 100.0, False, "error")
        assert not self.hm.can_execute("agent1")

    def test_audit_log(self):
        self.hm.kill("agent1", "test kill")
        self.hm.revive("agent1")
        log = self.hm.get_audit_log(limit=10)
        assert len(log) >= 2
        assert log[-2]["action"] == "kill"
        assert log[-1]["action"] == "revive"
