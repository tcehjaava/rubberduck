from .swebench import SWEBenchVerifiedInstance
from .leader import LeaderTaskSpec, LeaderReport, LeaderOutput
from .executor import ExecutorTaskSpec, ExecutorReport, ExecutorOutput

# Backwards compatibility aliases used by the rest of the code base
TaskSpec = LeaderTaskSpec
Report = ExecutorReport
Output = ExecutorOutput

__all__ = [
    "SWEBenchVerifiedInstance",
    "LeaderTaskSpec",
    "LeaderReport",
    "ExecutorTaskSpec",
    "ExecutorReport",
    "LeaderOutput",
    "ExecutorOutput",
]
