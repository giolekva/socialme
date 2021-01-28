load("@dependencies//:requirements.bzl", "requirement")

py_library(
    name = "db",
    srcs = ["db.py"],
)

py_library(
    name = "core",
    srcs = [
        "blog.py",
        "smileys.py",
    ],
    deps = [
        ":db",
        requirement("tornado"),
    ],
)

py_library(
    name = "sqlite",
    srcs = ["sqlite.py"],
    deps = [
        ":db",
    ],
)

py_binary(
    name = "socialme",
    srcs = ["main.py"],
    data = glob([
        "static/**",
        "templates/**",
        "*.json",
        "*.db",
    ]),
    main = "main.py",
    deps = [
        ":core",
        ":sqlite",
    ],
)

py_binary(
    name = "import_json",
    srcs = ["import_json.py"],
    deps = [
        ":db",
        ":sqlite",
    ],
)
