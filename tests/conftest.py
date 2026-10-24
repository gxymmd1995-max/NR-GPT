"""允许 CI 显式要求 MATLAB 向量，避免把跳过误报为对比通过。"""


def pytest_addoption(parser):
    parser.addoption("--require-matlab", action="store_true", help="Fail if MATLAB reference data is missing")
