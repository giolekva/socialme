import argparse
import json
from datetime import datetime
import pathlib

from db import Comment, Entry
import sqlite


def FlagsInit():
    parser = argparse.ArgumentParser(description="Import JSON formatted blog archive")
    parser.add_argument(
        "--archive",
        type=argparse.FileType("r", encoding="UTF-8"),
        help="Path to the JSON formatted blog archive",
    )
    parser.add_argument(
        "--db",
        type=pathlib.Path,
        help="Path to the SQLite file",
    )
    return parser.parse_args()


def ImportJson(entries, db):
    for e in entries:
        pubdate = datetime.strptime(e["PubDate"], "%Y-%m-%dT%H:%M:%SZ")
        entry = Entry(
            title=e["Title"],
            key=e["Slug"],
            body=e["Content"],
            tags=e["Tags"],
            published_time=pubdate,
            updated_time=pubdate,
            is_public=True,
            was_public=True,
        )
        db.EntriesSave(entry)
        thread = []
        for c in e["Comments"]:
            if c["Spam"] == True:
                continue
            parent = None
            for p in reversed(thread):
                if p["Margin"] + 20 == c["Margin"]:
                    parent = p["Comment"]
                    break
            comment = Comment(
                entry=entry,
                name=c["Author"],
                link=c["Url"] if len(c["Url"]) > 0 else None,
                email="noemail@email.com",
                email_md5=c["Gravatar"][
                    c["Gravatar"].rfind("/") + 1 : c["Gravatar"].rfind("?")
                ],
                comment=c["Comment"],
                parent_comment=parent,
                published_time=datetime.strptime(c["PubDate"], "%Y-%m-%dT%H:%M:%SZ"),
            )
            db.CommentsSave(comment)
            thread.append({"Comment": comment, "Margin": c["Margin"]})


def ReadEntries(inp):
    return json.loads(inp.read())


def Main():
    flags = FlagsInit()
    db = sqlite.OpenDB(flags.db)
    entries = ReadEntries(flags.archive)
    ImportJson(entries, db)


if __name__ == "__main__":
    Main()
