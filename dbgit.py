from datetime import datetime
import json

from db import DB, Comment, Entry


def IsEntry(item):
    return (
        item.type == "blob"
        and item.path.startswith("entries/")
        and item.path.endswith(".md")
    )


def IsComment(item):
    return (
        item.type == "blob"
        and item.path.startswith("comments/")
        and item.path.endswith(".json")
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


def ItemToComments(item):
    entry_key = item.path[item.path.find("/") + 1 : item.path.rfind(".")]
    kwargs = dict()
    data = item.data_stream.stream
    while True:
        line = data.readline().decode("UTF-8").strip()
        if len(line) == 0:
            break
        kwargs = json.loads(line)
        yield Comment(
            entry_key=entry_key,
            key=kwargs["key"],
            name=kwargs["name"],
            link=kwargs["link"],
            email=kwargs["email"],
            email_md5=kwargs["email_md5"],
            comment=kwargs["comment"],
            parent_comment_key=kwargs.get("parent_comment_key", None),
            published_time=datetime.strptime(
                kwargs["published_time"], "%Y-%m-%dT%H:%M:%SZ"
            ),
        )


class GitDB(DB):
    def __init__(self, repo, db):
        self._repo = repo
        self._db = db
        for item in repo.head.commit.tree.traverse():
            if IsEntry(item):
                entry = ItemToEntry(item)
                self._db.EntriesSave(entry)
        for item in repo.head.commit.tree.traverse():
            if IsComment(item):
                for comment in ItemToComments(item):
                    self._db.CommentsSave(comment)

    def EntriesGet(self, key):
        return self._db.EntriesGet(key)

    def EntriesGetPublic(self, count, after=None):
        return self._db.EntriesGetPublic(count, after)

    def EntriesDateRange(self, begin, end, count, after=None):
        return self._db.EntriesDateRange(begin, end, count, after)

    def EntriesPublicWithTag(self, tag, count, after=0):
        return self._db.EntriesPublicWithTag(tag, count, after)

    def EntriesGetPublishedTimes(self):
        return self._db.EntriesGetPublishedTimes()

    def EntriesSave(self, entry):
        self._db.EntriesSave(entry)

    def EntriesUpdate(self, entry, old_key):
        self._db.EntriesUpdate(entry, old_key)

    def TagsAll(self):
        return self._db.TagsAll()

    def Comments(self, count):
        return self._db.Comments(count)

    def CommentsGet(self, key):
        return self._db.CommentsGet(key)

    def CommentsForEntryWithKey(self, key):
        return self._db.CommentsForEntryWithKey(key)

    def CommentsCountForEntryWithKey(self, key):
        return self._db.CommentsCountForEntryWithKey(key)

    def CommentsSave(self, com):
        serialized = json.dumps(dict(com))
        comments_file = (
            self._repo.working_tree_dir + "/comments/" + com.entry.key + ".json"
        )
        with open(comments_file, "a") as out:
            out.write(serialized)
            out.write("\n")
        index = self._repo.index
        index.add([comments_file])
        index.commit("new comment")
        self._db.CommentsSave(com)
