from noodle.hooks import (
    before_all,
    before_feature,   # sets POM folder context — required for local pom.yaml lookup
    before_scenario,
    after_step,
    after_scenario,
    after_all,
)
