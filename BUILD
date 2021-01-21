load("@io_bazel_rules_appengine//appengine:py_appengine.bzl", "py_appengine_binary")
# load("@dependencies//:requirements.bzl", "requirement")

py_appengine_binary(
    name = "socialme",
    srcs = glob(["*.py"]),
    configs = [
        "app.yaml",
        "index.yaml",
    ],
    data = glob([
        "static/**",
        "templates/**",
    ]),
    deps = [
        # requirement("tornado"),
        ":tornado",
        # "@tornadoweb_tornado//:tornado",
    ],
)

# TODO(giolekva): Make pip or git dependency work instead.
py_library(
    name = "tornado",
    srcs = glob(["tornado/*.py"]),
)
