# NOTE(giolekva): this has not been tested after migrating from Appengine to SQLite

import argparse
import urllib
from xml import sax
import re

from db import Comment, Entry
import sqlite


def FlagsInit():
    parser = argparse.ArgumentParser(description="Import from Google Blogspot")
    parser.add_argument(
        "--blogger_id",
        type=str,
        help="Google Blogspot ID",
    )
    parser.add_argument(
        "--db",
        type=pathlib.Path,
        help="Path to the SQLite file",
    )
    return parser.parse_args()


# წასაშლელია, gdata-ს გამოყენება ჯობია
def to_date(s):
    s = s.encode("utf-8")
    pattern = re.compile(
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})\+(\d{2}):(\d{2})"
    )
    match = pattern.match(str(s))
    g = [int(x) for x in match.groups()]
    return datetime(g[0], g[1], g[2], g[3], g[4], g[5], g[6])


class CommentsHandler(sax.handler.ContentHandler):
    def __init__(self, entry, db):
        self.db = db
        self.content = ""
        self.email = ""
        self.entry = entry
        self.is_entry = 0
        self.is_published = 0
        self.is_content = 0
        self.is_name = 0
        self.is_uri = 0

    def startElement(self, name, attrs):
        self.content = ""
        if name == "entry":
            self.is_entry = 1
            self.link = ""
            self.email = "noemail@email.com"
        elif name == "published":
            self.is_published = 1
        elif name == "content":
            self.is_content = 1
        elif name == "name":
            self.is_name = 1
        elif name == "uri":
            self.is_uri = 1

    def endElement(self, name):
        if name == "entry":
            self.is_entry = 0
            com = Comment(
                entry=self.entry,
                name=self.name,
                link=self.link,
                email=self.email,
                comment=self.comment,
                published_time=self.published_time,
            )
            db.CommentsSave(com)
        elif name == "published":
            self.is_published = 0
            if self.is_entry:
                self.published_time = to_date(self.content)
        elif name == "content":
            self.is_content = 0
            if self.is_entry:
                self.comment = self.content
        elif name == "name":
            self.is_name = 0
            if self.is_entry:
                self.name = self.content
        elif name == "uri":
            self.is_uri = 0
            if self.is_entry:
                self.link = self.content

    def characters(self, ch):
        self.content += ch


class EntriesHandler(sax.handler.ContentHandler):
    def __init__(self, db):
        self.db = db
        self.content = ""
        self.is_entry = 0
        self.is_title = 0
        self.is_content = 0
        self.is_category = 0
        self.is_link = 0
        self.is_published = 0
        self.is_updated = 0
        self.link_count = 0

    def startElement(self, name, attrs):
        self.content = ""
        if name == "entry":
            self.is_entry = 1
            self.title = ""
            self.body = ""
            self.link_count = 0
            self.tags = []
        elif name == "title":
            self.is_title = 1
        elif name == "content":
            self.is_content = 1
        elif name == "category":
            self.is_category = 1
            self.tags.append(attrs.items()[0][1])
        elif name == "link":
            self.is_link = 1
            self.link_count += 1
            if self.is_entry and self.link_count == 1:
                self.comments_url = attrs.items()[0][1]
        elif name == "published":
            self.is_published = 1
        elif name == "updated":
            self.is_updated = 1

    def endElement(self, name):
        if name == "entry":
            self.is_entry = 0
            entry = Entry(
                key=self.title,  # TODO(giolekva): extract from url
                title=self.title,
                boddy=self.body,
                tags=self.tags,
                published_time=self.published_time,
                updated_time=self.updated,
                is_public=True,
                was_public=True,
            )
            db.EntriesSave(entry)
            ImportComments(self.comments_url, entry)
        elif name == "title":
            self.is_title = 0
            if self.is_entry:
                self.title = self.content
        elif name == "content":
            self.is_content = 0
            if self.is_entry:
                self.body = self.content
        elif name == "category":
            self.is_category = 0
        elif name == "link":
            self.is_link = 0
        elif name == "published":
            self.is_published = 0
            if self.is_entry:
                self.published_time = to_date(self.content)
        elif name == "updated":
            self.is_updated = 0
            if self.is_entry:
                self.updated = to_date(self.content)

    def characters(self, ch):
        self.content += ch


def ImportPosts(url, db):
    with urllib.urlopen(url) as inp:
        sax.parseString(inp.read(), EntriesHandler(db))


def ImportComments(url, entry, db):
    with urllib.urlopen(url) as inp:
        sax.parseString(inp.read(), CommentsHandler(entry, db))


def Main():
    flags = FlagsInit()
    db = sqlite.OpenDB(flags.db)
    url = "http://www.blogger.com/feeds/%s/posts/default" % flags.blogger_id
    ImportPosts(feed, db)


if __name__ == "__main__":
    Main()
