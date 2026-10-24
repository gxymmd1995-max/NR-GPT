"""示例运行日志：当前线程调用链、参数/出口值/耗时和完整对象快照。

使用 logging 与 sys.setprofile；不修改被观测类，不改变算法返回值。
详细用法、字段与限制见同级 ExampleLogger.md。
"""

from dataclasses import fields, is_dataclass
import inspect
import logging
import os
from pathlib import Path
import sys
import time
from types import FrameType


class ExampleLogger:
    """在 with 作用域内记录项目源码和一个示例入口的 Python 函数调用。"""

    def __init__(self, example_file: str | Path, console_level: str | None = None,
                 max_value_chars: int = 240) -> None:
        """指定示例文件；同级 .log 每次运行覆盖，完整变量快照不截断。

        console_level 未指定时读取 NR_LOG_LEVEL，默认 INFO。文件固定 DEBUG。
        max_value_chars 仅限制调用参数和出口值的 repr 长度，最小 32。
        """
        levels = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING,
                  "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL}
        level = console_level if console_level is not None else os.environ.get("NR_LOG_LEVEL", "INFO")
        if not isinstance(level, str) or level.upper() not in levels:
            raise ValueError("console_level / NR_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
        if type(max_value_chars) is not int or max_value_chars < 32:
            raise ValueError("max_value_chars must be an int >= 32")
        self.example_path = Path(example_file).resolve()
        self.log_path = self.example_path.with_suffix(".log")
        self.console_level = levels[level.upper()]
        self.max_value_chars = max_value_chars
        self.logger = logging.getLogger(f"nr-r15-phy.examples.{self.example_path.stem}.{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self._source_root = Path(__file__).resolve().parents[1]
        self._helper_path = Path(__file__).resolve()
        self._previous_profile = None
        self._stack: list[tuple[int, str, float]] = []
        self._code_info: dict[object, tuple[str, str] | None] = {}
        self._active = False
        self._suspended = False

    def __enter__(self) -> "ExampleLogger":
        """打开 UTF-8 文件/终端处理器并安装当前线程 profile 回调。"""
        if self._active:
            raise RuntimeError("ExampleLogger is already active")
        # FileHandler 打开失败时，尚未改变原 profiler 或 root logger。
        file_handler = logging.FileHandler(self.log_path, mode="w", encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        formatter = logging.Formatter("%(asctime)s UTC | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
        formatter.converter = time.gmtime
        for handler in (file_handler, console_handler):
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self._previous_profile = sys.getprofile()
        self._stack.clear()
        self._active = True
        self.logger.info("START example=%s log=%s", self.example_path.name, self.log_path)
        sys.setprofile(self._profile)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """恢复原 profiler、记录成功或异常、关闭处理器；不吞掉业务异常。"""
        sys.setprofile(self._previous_profile)
        self._active = False
        if exc_type is None:
            self.logger.info("FINISH status=OK")
        else:
            self.logger.error("FINISH status=FAILED", exc_info=(exc_type, exc_value, traceback))
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        self._stack.clear()
        return False

    def _describe_code(self, frame: FrameType) -> tuple[str, str] | None:
        """缓存可追踪代码的显示名称与位置；过滤自身、第三方和匿名推导式。"""
        code = frame.f_code
        if code in self._code_info:
            return self._code_info[code]
        info = None
        if not code.co_name.startswith("<"):
            # dataclass 生成的 __init__ 文件名是 <string>，用模块原文件归属判断。
            filename = frame.f_globals.get("__file__", "") if code.co_filename.startswith("<") else code.co_filename
            path = Path(filename).resolve()
            if path != self._helper_path and (path == self.example_path or path.is_relative_to(self._source_root)):
                if code.co_filename.startswith("<"):
                    owner = frame.f_locals.get("self")
                    name = f"{type(owner).__name__}.{code.co_name}"
                else:
                    name = code.co_qualname if "." in code.co_qualname else f"{path.stem}.{code.co_name}"
                location = f"<generated:{path.name}>" if code.co_filename.startswith("<") else f"{path.name}:{code.co_firstlineno}"
                info = (name, location)
        self._code_info[code] = info
        return info

    def _value_repr(self, value: object, truncate: bool = True) -> str:
        """安全格式化值；调用参数按长度截断，状态快照可要求完整输出。"""
        try:
            result = repr(value)
        except Exception as error:
            result = f"<repr failed: {type(error).__name__}>"
        if truncate and len(result) > self.max_value_chars:
            result = result[:self.max_value_chars] + "...<truncated>"
        return result

    def _arguments(self, frame: FrameType) -> str:
        """读取当前调用的参数；self/cls 仅显示类型，避免未初始化对象 repr。"""
        arguments = inspect.getargvalues(frame)
        names = arguments.args + [name for name in (arguments.varargs, arguments.keywords) if name is not None]
        parts = []
        for name in names:
            value = arguments.locals[name]
            shown = f"<{type(value).__name__}>" if name in ("self", "cls") else self._value_repr(value)
            parts.append(f"{name}={shown}")
        return ", ".join(parts)

    def _profile(self, frame: FrameType, event: str, arg: object) -> None:
        """处理 call/return：缩进、完整调用路径、参数、出口值和毫秒耗时。"""
        if self._suspended or event not in ("call", "return"):
            return
        if event == "call":
            info = self._describe_code(frame)
            if info is not None:
                name, location = info
                self._stack.append((id(frame), name, time.perf_counter()))
                path = " -> ".join(item[1] for item in self._stack)
                self.logger.debug("%sCALL %s(%s) | path=%s | source=%s", "  " * (len(self._stack) - 1),
                                  name, self._arguments(frame), path, location)
        elif self._stack and self._stack[-1][0] == id(frame):
            _, name, started = self._stack.pop()
            self.logger.debug("%sEXIT %s | value=%s | elapsed_ms=%.3f", "  " * len(self._stack), name,
                              self._value_repr(arg), (time.perf_counter() - started) * 1000)

    def dump_state(self, instance: object, label: str = "instance") -> dict[str, dict[str, object]]:
        """完整记录 dataclass 字段、类常量及 property，返回分组快照。

        支持普通有 __dict__ 的对象；快照期间暂停调用链记录以避免递归噪声。
        property 求值失败时记录异常占位字符串，其他成员继续输出。
        未进入 with 作用域时抛 RuntimeError。
        """
        if not self._active:
            raise RuntimeError("dump_state requires an active ExampleLogger context")
        self._suspended = True
        try:
            values = {field.name: getattr(instance, field.name) for field in fields(instance)} if is_dataclass(instance) else dict(vars(instance))
            state: dict[str, dict[str, object]] = {"fields": values, "constants": {}, "properties": {}}
            for base in reversed(type(instance).__mro__):
                for name, member in vars(base).items():
                    if name.isupper():
                        state["constants"][name] = member
                    elif isinstance(member, property) and not name.startswith("_"):
                        try:
                            state["properties"][name] = getattr(instance, name)
                        except Exception as error:
                            state["properties"][name] = f"<error: {type(error).__name__}: {error}>"
            self.logger.info("STATE %s class=%s", label, type(instance).__name__)
            for group, members in state.items():
                for name, value in members.items():
                    self.logger.info("STATE %s.%s.%s = %s", label, group, name, self._value_repr(value, truncate=False))
            return state
        finally:
            self._suspended = False
