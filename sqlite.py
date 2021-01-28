from datetime import datetime
import sqlite3

import db


_CREATE_ENTRY_TABLE = """
CREATE TABLE Entry (
  key VARCHAR(255) PRIMARY KEY,
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
  entry_key VARCHAR(255),
  name VARCHAR(255),
  link VARCHAR(255),
  email VARCHAR(255),
  email_md5 VARCHAR(255),
  comment TEXT,
  parent_comment_key VARCHAR(50),
  published_time INTEGER
);
"""

_ENTRIES_GET = """
SELECT
  key,
  title,
  body,
  tags,
  published_time,
  updated_time,
  is_public,
  was_public
FROM Entry
WHERE
  key = :key
"""

_ENTRIES_GET_PUBLIC = """
SELECT
  key,
  title,
  body,
  tags,
  published_time,
  updated_time,
  is_public,
  was_public
FROM Entry
WHERE
  is_public = :is_public
ORDER BY
  published_time DESC
LIMIT :count
"""

_ENTRIES_DATE_RANGE = """
SELECT
  key,
  title,
  body,
  tags,
  published_time,
  updated_time,
  is_public,
  was_public
FROM Entry
WHERE
  is_public = :is_public AND
  :from <= published_time AND published_time < :to
ORDER BY
  published_time DESC
LIMIT :count
"""

_ENTRIES_PUBLIC_WITH_TAG = """
SELECT
  key,
  title,
  body,
  tags,
  published_time,
  updated_time,
  is_public,
  was_public
FROM Entry
WHERE
  is_public = :is_public AND
  instr(tags, :tag) > 0
ORDER BY
  published_time DESC
LIMIT :count
"""

_ENTRIES_PUBLISHED_TIMES = """
SELECT
  published_time
FROM Entry
WHERE
  is_public = :is_public
"""


_ENTRIES_SAVE = """
INSERT INTO Entry (
  key,
  title,
  body,
  tags,
  published_time,
  updated_time,
  is_public,
  was_public)
VALUES (
  :key,
  :title,
  :body,
  :tags,
  :published_time,
  :updated_time,
  :is_public,
  :was_public)
"""

_TAGS_ALL = """
SELECT
  tags
FROM Entry
WHERE
  is_public = :is_public
"""

_COMMENTS = """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.key,
  Entry.title,
  Entry.body,
  Entry.tags,
  Entry.published_time,
  Entry.updated_time,
  Entry.is_public,
  Entry.was_public
FROM Comment
JOIN Entry ON
  Comment.entry_key = Entry.key
ORDER BY
  Comment.published_time DESC
LIMIT :count
"""

_COMMENTS_GET = """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.key,
  Entry.title,
  Entry.body,
  Entry.tags,
  Entry.published_time,
  Entry.updated_time,
  Entry.is_public,
  Entry.was_public
FROM Comment
JOIN Entry ON
  Comment.entry_key = Entry.key
WHERE
  Comment.key = :key
"""

_COMMENTS_FOR_ENTRY_WITH_KEY = """
SELECT
  Comment.key,
  Comment.name,
  Comment.link,
  Comment.email,
  Comment.email_md5,
  Comment.comment,
  Comment.parent_comment_key,
  Comment.published_time,
  Entry.key,
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
  Comment.entry_key = Entry.key
WHERE
  Comment.entry_key = :key
ORDER BY
  Comment.published_time ASC
"""

_COMMENTS_COUNT_FOR_ENTRY_WITH_KEY = """
SELECT
  COUNT(*)
FROM Comment
WHERE
  entry_key = :key
"""

_COMMENTS_SAVE = """
INSERT INTO Comment (
  key,
  entry_key,
  name,
  link,
  email,
  email_md5,
  comment,
  parent_comment_key,
  published_time)
VALUES (
  :key,
  :entry_key,
  :name,
  :link,
  :email,
  :email_md5,
  :comment,
  :parent_comment_key,
  :published_time)
"""


def CreateTables(conn):
    c = conn.cursor()
    c.execute(_CREATE_ENTRY_TABLE)
    c.execute(_CREATE_COMMENT_TABLE)
    conn.commit()


def DatetimeToTimestamp(ts):
    return ts.timestamp()


def CreateSqliteConn(db_path):
    sqlite3.register_adapter(datetime, DatetimeToTimestamp)
    conn = sqlite3.connect(db_path)
    try:
        CreateTables(conn)
    except:
        pass
    return conn


def OpenDB(db_path):
    return DB(CreateSqliteConn(db_path))


def ToEntry(r):
    if r is None:
        return None
    return db.Entry(
        key=r[0],
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

    def EntriesGet(self, key):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_GET,
            {"key": key},
        )
        return ToEntry(c.fetchone())

    def EntriesGetPublic(self, count, after=None):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_GET_PUBLIC,
            {
                "is_public": True,
                "count": count,
            },
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesDateRange(self, begin, end, count, after=None):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_DATE_RANGE,
            {
                "is_public": True,
                "from": datetime.timestamp(begin),
                "to": datetime.timestamp(end),
                "count": count,
            },
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesPublicWithTag(self, tag, count, after=0):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_PUBLIC_WITH_TAG,
            {
                "is_public": True,
                "tag": tag,
                "count": count,
            },
        )
        return List([ToEntry(e) for e in c.fetchall()])

    def EntriesGetPublishedTimes(self):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_PUBLISHED_TIMES,
            {"is_public": True},
        )
        return List([datetime.fromtimestamp(e[0]) for e in c.fetchall()])

    def EntriesSave(self, e):
        c = self.conn.cursor()
        c.execute(
            _ENTRIES_SAVE,
            {
                "key": e.key,
                "title": e.title,
                "body": e.body,
                "tags": ",".join(e.tags),
                "published_time": e.published_time,
                "updated_time": e.updated_time,
                "is_public": e.is_public,
                "was_public": e.was_public,
            },
        )
        self.conn.commit()

    def TagsAll(self):
        c = self.conn.cursor()
        c.execute(_TAGS_ALL, {"is_public": True})
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
            _COMMENTS,
            {"count": count},
        )
        return List([ToComment(c) for c in c.fetchall()])

    def CommentsGet(self, key):
        c = self.conn.cursor()
        c.execute(
            _COMMENTS_GET,
            {"key": key},
        )
        return ToComment(c.fetchonme())

    def CommentsForEntryWithKey(self, key):
        c = self.conn.cursor()
        c.execute(
            _COMMENTS_FOR_ENTRY_WITH_KEY,
            {"key": key},
        )
        return List([ToComment(c) for c in c.fetchall()])

    def CommentsCountForEntryWithKey(self, key):
        c = self.conn.cursor()
        c.execute(_COMMENTS_COUNT_FOR_ENTRY_WITH_KEY, {"key": key})
        return c.fetchone()[0]

    def CommentsSave(self, com):
        parent_comment_key = None
        if com.parent_comment:
            parent_comment_key = com.parent_comment.key
        c = self.conn.cursor()
        c.execute(
            _COMMENTS_SAVE,
            {
                "key": com.key,
                "entry_key": com.entry.key,
                "name": com.name,
                "link": com.link,
                "email": com.email,
                "email_md5": com.email_md5,
                "comment": com.comment,
                "parent_comment_key": parent_comment_key,
                "published_time": com.published_time,
            },
        )
        self.conn.commit()
