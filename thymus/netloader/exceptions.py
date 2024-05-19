from __future__ import annotations


class TimeoutError(Exception):
    def __init__(self, ip_address: str) -> None:
        self.ip_address = ip_address
        super().__init__(f'Timeout error for host "{ip_address}".')


class DisconnectError(Exception):
    def __init__(self, ip_address: str, code: int, reason: str, protocol: str) -> None:
        self.ip_address = ip_address
        self.code = code
        self.reason = reason
        super().__init__(f'Disconnect error from {ip_address}, protocol: {protocol}. Reason: "{reason}".')


class KeyError(Exception):
    def __init__(self, ip_address: str, code: int, reason: str) -> None:
        self.ip_address = ip_address
        self.code = code
        self.reason = reason
        super().__init__(f'SSH key error for {ip_address}. Reason: "{reason}".')
