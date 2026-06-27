from behave import use_step_matcher, step
from bddframe.orchestrator.visual_runner import execute_visual_step

use_step_matcher("re")


@step(r"(?P<anything>.*)")
def visual_catch_all(context, anything):
    execute_visual_step(anything)
