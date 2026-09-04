"""Exclusive motion ownership with fail-closed watchdog (not a safety PLC)."""
import time
import uuid


class MeasurementLease:
    def __init__(self, timeout_s=30.0, clock=time.monotonic):
        self.token = ""
        self.deadline = 0.0
        self.failed = False
        self.timeout_s = timeout_s
        self.clock = clock
        self.epoch = uuid.uuid4().hex

    def update(self, command, token, idle):
        if not token:
            return False
        if command == "acquire" and not self.token and idle:
            self.token = token
            self.failed = False
            self.deadline = self.clock()+self.timeout_s
            return True
        if token != self.token:
            return False
        if command == "renew" and not self.failed and self.clock() < self.deadline:
            self.deadline = self.clock()+self.timeout_s
            return True
        if command == "release" and idle:
            self.token = ""
            return True
        return False

    def permits(self, token):
        return not self.token or (token == self.token and not self.failed and self.clock() < self.deadline)

    def expired(self):
        if self.token and not self.failed and self.clock() >= self.deadline:
            self.failed = True
            return True
        return False

    def invalidate_reference(self):
        self.epoch = uuid.uuid4().hex
