from behave import use_step_matcher, step
from bddframe.orchestrator.runner import execute_step
from bddframe.orchestrator.visual_runner import execute_visual_step

# Regex matcher so [variable] brackets in step text don't confuse the parser
use_step_matcher("re")


@step(r"(?P<anything>.*)")
def catch_all(context, anything):
    # Single catch-all for the whole suite: web and visual cannot both register
    # the same regex (behave raises AmbiguousStep), so we route by tag here.
    # @visual → desktop/OpenCV agent; everything else → web (Playwright) agent.
    tags = set(getattr(context.scenario, "effective_tags", None) or [])
    if "visual" in tags:
        execute_visual_step(anything)
    else:
        execute_step(anything, context)
