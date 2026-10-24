"""诊断系统的调用链、完整快照、输出隔离、错误传播和资源清理。"""

import inspect
from io import StringIO
import logging
import sys
from types import SimpleNamespace

import pytest

from cell import NRCell
from diagnostics import ExampleLogger


def test_call_chain_and_complete_snapshot(tmp_path, capsys):
    root_handlers = logging.getLogger().handlers[:]
    previous = sys.getprofile()
    log = ExampleLogger(tmp_path / "sample.py")
    with log:
        cell = NRCell(n_cell_id=42)
        state = log.dump_state(cell, "cell")
        assert cell.symbol_timing(0)["total_samples"] == 1112
        log.logger.info("A useful message")
    assert sys.getprofile() is previous
    assert logging.getLogger().handlers == root_handlers
    assert not log.logger.handlers
    assert len(state["fields"]) == 12
    assert len(state["constants"]) == 8
    assert len(state["properties"]) == 35
    text = log.log_path.read_text(encoding="utf-8")
    assert "CALL NRCell.__init__" in text
    assert "<generated:NRCell.py>" in text
    assert "CALL NRCell.symbol_timing" in text
    assert "path=NRCell.symbol_timing -> NRCell.symbol_start_samples" in text
    assert "elapsed_ms=" in text
    assert "STATE cell.properties.cp_lengths_samples = " + repr(cell.cp_lengths_samples) in text
    assert "FINISH status=OK" in text
    assert "A useful message" in text
    console = capsys.readouterr().out
    assert "STATE cell.fields.n_cell_id = 42" in console
    assert "CALL NRCell.symbol_timing" not in console


def test_debug_environment_and_overwrite(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NR_LOG_LEVEL", "debug")
    example = tmp_path / "sample.py"
    log = ExampleLogger(example)
    with log:
        NRCell().prb_to_crb(0)
    assert "CALL NRCell.prb_to_crb" in capsys.readouterr().out
    with log:
        log.logger.info("Only second run")
    assert "CALL NRCell.prb_to_crb" not in log.log_path.read_text(encoding="utf-8")
    assert "Only second run" in log.log_path.read_text(encoding="utf-8")


def test_exceptions_propagate_and_profiler_is_restored(tmp_path):
    def previous_profile(frame, event, arg):
        return None

    original = sys.getprofile()
    sys.setprofile(previous_profile)
    try:
        log = ExampleLogger(tmp_path / "failed.py", console_level="ERROR")
        with pytest.raises(ValueError, match="prb"):
            with log:
                NRCell().prb_to_crb(-1)
        assert sys.getprofile() is previous_profile
        text = log.log_path.read_text(encoding="utf-8")
        assert "FINISH status=FAILED" in text
        assert "Traceback" in text
        assert "ValueError" in text
        assert not log.logger.handlers
    finally:
        sys.setprofile(original)


@pytest.mark.parametrize("level", ["UNKNOWN", 10, []])
def test_invalid_console_level(tmp_path, level):
    with pytest.raises(ValueError, match="console_level"):
        ExampleLogger(tmp_path / "sample.py", console_level=level)


@pytest.mark.parametrize("length", [0, 31, True, "240"])
def test_invalid_repr_limit(tmp_path, length):
    with pytest.raises(ValueError, match="max_value_chars"):
        ExampleLogger(tmp_path / "sample.py", max_value_chars=length)


def test_usage_guards_and_unavailable_output(tmp_path):
    log = ExampleLogger(tmp_path / "sample.py")
    with pytest.raises(RuntimeError, match="active"):
        log.dump_state(NRCell())
    with log:
        with pytest.raises(RuntimeError, match="already active"):
            log.__enter__()
    previous = sys.getprofile()
    with pytest.raises(FileNotFoundError):
        with ExampleLogger(tmp_path / "missing" / "sample.py"):
            pytest.fail("not reached")
    assert sys.getprofile() is previous


def test_repr_limits_and_failures(tmp_path, monkeypatch):
    log = ExampleLogger(tmp_path / "sample.py", max_value_chars=32)
    assert log._value_repr("x" * 100).endswith("...<truncated>")
    assert log._value_repr("x" * 100, truncate=False) == repr("x" * 100)
    monkeypatch.setattr(NRCell, "__repr__", lambda self: 1 / 0)
    assert log._value_repr(NRCell()) == "<repr failed: ZeroDivisionError>"


def test_property_errors_and_plain_instance(tmp_path, monkeypatch):
    def fail(instance):
        raise ValueError("failed getter")

    monkeypatch.setattr(NRCell, "n_fft", property(fail))
    with ExampleLogger(tmp_path / "sample.py", console_level="ERROR") as log:
        state = log.dump_state(NRCell(), "broken")
        assert state["properties"]["n_fft"] == "<error: ValueError: failed getter>"
        assert state["fields"]["n_cell_id"] == 1
        assert not log._suspended
        plain = log.dump_state(SimpleNamespace(answer=42), "plain")
        assert plain == {"fields": {"answer": 42}, "constants": {}, "properties": {}}


def test_example_scope_arguments_and_noise_filter(tmp_path):
    example = tmp_path / "example.py"
    code = compile("def operation(a, *args, **kwargs):\n    return a\n", str(example), "exec")
    namespace = {"__file__": str(example)}
    exec(code, namespace)
    with ExampleLogger(example, console_level="ERROR") as log:
        assert namespace["operation"](7, 8, note="hello") == 7
        # 用户作用域外和匿名推导式不记录，但其内部调用到 NRCell 时仍可记录。
        list(value for value in range(2))
        log._profile(inspect.currentframe(), "c_call", None)
        log._profile(inspect.currentframe(), "return", None)
    text = log.log_path.read_text(encoding="utf-8")
    assert "CALL example.operation(a=7, args=(8,), kwargs={'note': 'hello'})" in text
    assert "CALL logging." not in text
    assert "CALL <genexpr>" not in text


def test_profile_events_directly_with_coverage(tmp_path):
    """CPython 在 profile 回调内抑制 trace；直接注入事件另验证状态机与分支。"""
    example = tmp_path / "example.py"
    log = ExampleLogger(example)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    log.logger.addHandler(handler)
    namespace = {"__file__": str(example), "log": log, "inspect": inspect}
    exec(compile(
        "def outer(a, *args, **kwargs):\n"
        "    frame = inspect.currentframe()\n"
        "    log._profile(frame, 'call', None)\n"
        "    inner()\n"
        "    log._profile(frame, 'return', a)\n"
        "def inner(self=None):\n"
        "    frame = inspect.currentframe()\n"
        "    log._profile(frame, 'call', None)\n"
        "    log._profile(frame, 'return', None)\n",
        str(example), "exec"), namespace)
    namespace["outer"](7, 8, note="hello")
    namespace["outer"](9)  # 第二次调用覆盖代码信息缓存命中。
    assert not log._stack
    text = stream.getvalue()
    assert "path=example.outer -> example.inner" in text
    assert "self=<NoneType>" in text
    assert "args=(8,), kwargs={'note': 'hello'}" in text
    assert "EXIT example.outer | value=7" in text
    frame = inspect.currentframe()
    log._profile(frame, "call", None)  # 此测试代码不在追踪范围。
    log._profile(frame, "return", None)
    log._profile(frame, "c_call", None)
    log._suspended = True
    log._profile(frame, "call", None)
    log._suspended = False
    # 匿名推导式明确不追踪。
    assert next(log._describe_code(inspect.currentframe()) for _ in range(1)) is None
    # 独立生成类构造器，验证 <string> 定位，而不是把生成代码位置当作源码行号。
    generated = {"__file__": str(example), "log": log, "inspect": inspect}
    exec(compile("def created(self):\n    return log._describe_code(inspect.currentframe())\n", "<string>", "exec"), generated)
    assert generated["created"](NRCell()) == ("NRCell.created", "<generated:example.py>")
    log.logger.removeHandler(handler)
    handler.close()
