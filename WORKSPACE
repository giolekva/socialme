load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository", "new_git_repository")

# AppEngine

git_repository(
    name = "io_bazel_rules_appengine",
    remote = "https://github.com/bazelbuild/rules_appengine.git",
    # Check https://github.com/bazelbuild/rules_appengine/releases for the latest version.
    tag = "0.0.9",
)

load(
    "@io_bazel_rules_appengine//appengine:sdk.bzl",
    "appengine_repositories",
)

appengine_repositories()

load(
    "@io_bazel_rules_appengine//appengine:py_appengine.bzl",
    "py_appengine_repositories",
)

py_appengine_repositories()

# # Tornado

# http_archive(
#     name = "rules_python",
#     url = "https://github.com/bazelbuild/rules_python/releases/download/0.1.0/rules_python-0.1.0.tar.gz",
#     sha256 = "b6d46438523a3ec0f3cead544190ee13223a52f6a6765a29eae7b7cc24cc83a0",
# )

# load("@rules_python//python:pip.bzl", "pip_install")

# # Create a central repo that knows about the dependencies needed for
# # requirements.txt.
# pip_install(
#    name = "dependencies",
#    requirements = "//:requirements.txt",
# )

# new_git_repository(
#     name = "tornadoweb_tornado",
#     remote = "https://github.com/tornadoweb/tornado.git",
#     # Check https://github.com/bazelbuild/rules_appengine/releases for the latest version.
#     tag = "v1.0.0",
#     build_file_content = """
# py_library(
#   name = "tornado",
#   srcs = glob(["tornado/*.py"]),
#   visibility = ["//visibility:public"],
# )
# """
# )
