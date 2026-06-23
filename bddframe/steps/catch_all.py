from behave import use_step_matcher, step
from bddframe.orchestrator.runner import execute_step

# Regex matcher so [variable] brackets in step text don't confuse the parser
use_step_matcher("re")


@step(r"(?P<anything>.*)")
def catch_all(context, anything):
    execute_step(anything, context)
