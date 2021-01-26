from datetime import datetime

import db

_CREATE_ENTRY_TABLE = """
CREATE TABLE Entry (
  slug VARCHAR(255) PRIMARY KEY,
  title VARCHAR(255),
  body TEXT,
  tags TEXT,
  published_time INTEGER,
  updated_time INTEGER,
  is_public INTEGER,
  was_public INTEGER
);
"""

_CREATE_COMMENT_TABLE = """
CREATE TABLE Comment (
  key VARCHAR(50) PRIMARY KEY,
  entry_slug VARCHAR(255),
  name VARCHAR(255),
  link VARCHAR(255),
  email VARCHAR(255),
  email_md5 VARCHAR(255),
  comment TEXT,
  parent_comment_key VARCHAR(50),
  published_time INTEGER
);
"""


def CreateTables(conn):
    c = conn.cursor()
    c.execute(_CREATE_ENTRY_TABLE)
    c.execute(_CREATE_COMMENT_TABLE)
    conn.commit()


def ToEntry(r):
    if r is None:
        return None
    return db.Entry(
        key=r[0],
        slug=r[0],
        title=r[1],
        body=r[2],
        tags=r[3].split(","),
        published_time=datetime.fromtimestamp(r[4]),
        updated_time=datetime.fromtimestamp(r[5]),
        is_public=r[6],
        was_public=r[7],
    )


def ToComment(r):
    if r is None:
        return None
    c = db.Comment(
        key=r[0],
        name=r[1],
        link=r[2],
        email=r[3],
        email_md5=r[4],
        comment=r[5],
        published_time=datetime.fromtimestamp(r[7]),
        entry=ToEntry(r[8:]),
    )
    if r[6]:
        c.parent_comment = db.Comment(key=r[6])
    return c


def List(a):
    if a is None:
        return []
    return a


class DB(db.DB):
    def __init__(self, conn):
        self.conn = conn

    def EntriesGet(self, slug):
        c = self.conn.cursor()
        c.execute(
            "SELECT slug, title, body, tags, published_time, updated_time, is_public, was_public FROM Entry WHERE slug = ?",
            (slug,),
        )
        return ToEntry(c.fetchone())

    def EntriesGetWithKey(self, key):
        return EntriesGet(key)

    def EntriesGetPublic(self, count, after=None):
        c = self.conn.cursor()
        c.execute(
            "SELECT slug, title, body, tags, published_time, updated_time, is_public, was_public FROM Entry WHERE is_public = ? LIMIT ?",
            (
                True,
                count,
            ),
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesDateRange(self, begin, end, count, after=None):
        c = self.conn.cursor()
        c.execute(
            "SELECT slug, title, body, tags, published_time, updated_time, is_public, was_public FROM Entry WHERE is_public = ? AND ? <= published_time AND published_time < ? LIMIT ?",
            (
                True,
                datetime.timestamp(begin),
                datetime.timestamp(end),
                count,
            ),
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesPublicWithTag(self, tag, count, after=0):
        c = self.conn.cursor()
        c.execute(
            "SELECT slug, title, body, tags, published_time, updated_time, is_public, was_public FROM Entry WHERE is_public = ? AND instr(tags, ?) > 0 LIMIT ?",
            (
                True,
                tag,
                count,
            ),
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesGetPublishedTimes(self):
        c = self.conn.cursor()
        c.execute("SELECT published_time FROM Entry WHERE is_public = ?", (True,))
        return List([datetime.fromtimestamp(e[0]) for e in c.fetchall()])

    def EntriesSave(self, e):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO Entry (slug, title, body, tags, published_time, updated_time, is_public, was_public) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                e.slug,
                e.title,
                e.body,
                ",".join(e.tags),
                e.published_time,
                e.updated_time,
                e.is_public,
                e.was_public,
            ),
        )
        self.conn.commit()
        e.key = e.slug

    def TagsAll(self):
        c = self.conn.cursor()
        c.execute("SELECT tags FROM Entry WHERE is_public = ?", (True,))
        counts = {}
        for e in c.fetchall():
            for tag in e[0].split(","):
                if tag in counts:
                    counts[tag] += 1
                else:
                    counts[tag] = 1
        return List([db.Tag(tag, count) for (tag, count) in counts.items()])

    def Comments(self, count):
        c = self.conn.cursor()
        c.execute(
            """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.slug,
  Entry.title,
  Entry.body,
  Entry.tags,
  Entry.published_time,
  Entry.updated_time,
  Entry.is_public,
  Entry.was_public
FROM
  Comment
JOIN Entry ON
  Comment.entry_slug = Entry.slug
ORDER BY
  Comment.published_time DESC
LIMIT ?""",
            (count,),
        )
        return List([ToComment(c) for c in c.fetchall()])

    def CommentsGet(self, id):
        c = self.conn.cursor()
        c.execute(
            """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.slug,
  Entry.title,
  Entry.body,
  Entry.tags,
  Entry.published_time,
  Entry.updated_time,
  Entry.is_public,
  Entry.was_public
FROM
  Comment
JOIN Entry ON
  Comment.entry_slug = Entry.slug
WHERE
  Comment.key = ?""",
            (id,),
        )
        return ToComment(c.fetchonme())

    def CommentsForEntryWithKey(self, key):
        c = self.conn.cursor()
        c.execute(
            """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.slug,
  Entry.title,
  Entry.body,
  Entry.tags,
  Entry.published_time,
  Entry.updated_time,
  Entry.is_public,
  Entry.was_public
FROM
  Comment
JOIN Entry ON
  Comment.entry_slug = Entry.slug
WHERE
  Comment.entry_slug = ?
ORDER BY
  Comment.published_time ASC""",
            (key,),
        )
        return List([ToComment(c) for c in c.fetchall()])

    def CommentsCountForEntryWithKey(self, key):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM Comment WHERE entry_slug = ?", (key,))
        return c.fetchone()[0]

    def CommentsSave(self, com):
        parent_comment_key = None
        if com.parent_comment:
            parent_comment_key = com.parent_comment.key
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO Comment (key, entry_slug, name, link, email, email_md5, comment, parent_comment_key, published_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                com.md5(),
                com.entry.slug,
                com.name,
                com.link,
                com.email,
                com.email_md5,
                com.comment,
                parent_comment_key,
                com.published_time,
            ),
        )
        self.conn.commit()
        com.key = com.md5()
