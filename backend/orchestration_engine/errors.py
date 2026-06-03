from __future__ import annotations


class OrchestrationEngineError(RuntimeError):
    pass


class ValidationError(OrchestrationEngineError):
    pass


class LowcodeCompileError(OrchestrationEngineError):
    pass


class LowcodeRuntimeError(OrchestrationEngineError):
    pass


class LowcodeTimeoutError(OrchestrationEngineError):
    pass


class LowcodeProtocolError(OrchestrationEngineError):
    pass


class LoopContinueSignal(OrchestrationEngineError):
    pass


class LoopBreakSignal(OrchestrationEngineError):
    pass


class RunCancelledError(OrchestrationEngineError):
    pass
