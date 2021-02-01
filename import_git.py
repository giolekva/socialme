import argparse
from datetime import datetime
import git
import pathlib

from db import Entry
import sqlite


def FlagsInit():
    parser = argparse.ArgumentParser(
        description="Import blog entries from git repository"
    )
    parser.add_argument("--repo", type=pathlib.Path, help="Path to the git repository")
    parser.add_argument(
        "--db",
        type=pathlib.Path,
        help="Path to the SQLite file",
    )
    return parser.parse_args()


def IsEntry(item):
    return (
        item.type == "blob"
        and item.path.startswith("entries/")
        and item.path.endswith(".md")
    )


def ItemToEntry(item):
    key = item.path[item.path.find("/") + 1 : item.path.rfind(".")]
    kwargs = dict()
    data = item.data_stream.stream
    while True:
        line = data.readline().decode("UTF-8").strip()
        if line == "---":
            break
        elif len(line) == 0:
            continue
        attr, value = line.split(":", 1)
        kwargs[attr.strip()] = value.strip()
    kwargs["body"] = data.read().decode("UTF-8")
    kwargs["pubdate"] = datetime.strptime(kwargs["pubdate"], "%Y-%m-%dT%H:%M:%SZ")
    return Entry(
        key=key,
        title=kwargs["title"],
        body=kwargs["body"],
        tags=map(lambda x: x.strip(), kwargs.get("tags", "").split(",")),
        published_time=kwargs["pubdate"],
        updated_time=kwargs["pubdate"],
        is_public=True,
        was_public=True,
        is_markdown=True,
    )


def Main():
    flags = FlagsInit()
    repo = git.Repo(flags.repo)
    db = sqlite.OpenDB(flags.db)
    for item in repo.head.commit.tree.traverse():
        if IsEntry(item):
            entry = ItemToEntry(item)
            db.EntriesSave(entry)


if __name__ == "__main__":
    Main()
