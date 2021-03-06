from datetime import datetime
import hashlib
import re
from markdown import markdown


class Entry(object):
    def __init__(
        self,
        key=None,
        title=None,
        body=None,
        tags=None,
        published_time=None,
        updated_time=None,
        is_public=None,
        was_public=None,
        is_markdown=False,
    ):
        self.key = key
        self.title = title
        self.body = body
        self.tags = tags
        self.published_time = published_time
        self.updated_time = updated_time
        self.is_public = is_public
        self.was_public = was_public
        self.is_markdown = is_markdown

    def get_paragraphs(self):
        pattern = re.compile(r"^\s*(?P<line>.*?)\s*$", re.S | re.M | re.X)
        return pattern.sub("<p>\g<line></p>", self.body)

    # TODO(giolekva): move this out
    def Format(self):
        if not self.is_markdown:
            return self.body
        return markdown(self.body)


class Tag(object):
    def __init__(self, name=None, count=None):
        self.name = name
        self.count = count


class Comment(object):
    def __init__(
        self,
        key=None,
        entry=None,
        entry_key=None,
        name=None,
        link=None,
        email=None,
        email_md5=None,
        comment=None,
        parent_comment=None,
        parent_comment_key=None,
        published_time=None,
    ):
        if key:
            self._key = key
        self.entry = entry
        if entry_key:
            self._entry_key = entry_key
        self.name = name
        self.link = link
        self.email = email
        if email_md5:
            self._email_md5 = email_md5
        self.comment = comment
        self.parent_comment = parent_comment
        if parent_comment_key:
            self._parent_comment_key = parent_comment_key
        self.published_time = published_time

    def __iter__(self):
        yield ("entry_key", self.entry.key)
        if self.parent_comment:
            yield ("parent_comment_key", self.parent_comment.key)
        yield (
            "published_time",
            datetime.strftime(self.published_time, "%Y-%m-%dT%H:%M:%SZ"),
        )
        for k in ["key", "name", "link", "email", "email_md5", "comment"]:
            yield (k, getattr(self, k))

    @property
    def email_md5(self):
        if not hasattr(self, "_email_md5"):
            m = hashlib.md5()
            m.update(self.email.encode("UTF-8"))
            self._email_md5 = m.hexdigest()
        return self._email_md5

    @property
    def key(self):
        if not hasattr(self, "_key"):
            m = hashlib.md5()
            m.update(self.entry.key.encode("UTF-8"))
            m.update(self.name.encode("UTF-8"))
            if self.link:
                m.update(self.link.encode("UTF-8"))
            m.update(self.email_md5.encode("UTF-8"))
            m.update(self.comment.encode("UTF-8"))
            if self.parent_comment:
                m.update(self.parent_comment.key.encode("UTF-8"))
            m.update(str(datetime.timestamp(self.published_time)).encode("UTF-8"))
            self._key = m.hexdigest()
        return self._key

    @property
    def entry_key(self):
        if hasattr(self, "_entry_key"):
            return self._entry_key
        return self.entry.key

    @property
    def parent_comment_key(self):
        if hasattr(self, "_parent_comment_key"):
            return self._parent_comment_key
        if self.parent_comment:
            return self.parent_comment.key
        return None


class Archive(object):
    def __init__(self, year, month, count):
        self.year = year
        self.month = month
        self.count = count


class DB(object):
    def EntriesGet(self, key):
        raise NotImplementedError

    def EntriesGetPublic(self, count, after=None):
        raise NotImplementedError

    def EntriesDateRange(self, begin, end, count, after=None):
        raise NotImplementedError

    def EntriesPublicWithTag(self, tag, count, after=0):
        raise NotImplementedError

    def EntriesGetPublishedTimes(self):
        raise NotImplementedError

    def EntriesSave(self, entry):
        raise NotImplementedError

    def EntriesUpdate(self, entry, old_key):
        raise NotImplementedError

    def TagsAll(self):
        raise NotImplementedError

    def Comments(self, count):
        raise NotImplementedError

    def CommentsGet(self, key):
        raise NotImplementedError

    def CommentsForEntryWithKey(self, key):
        raise NotImplementedError

    def CommentsCountForEntryWithKey(self, key):
        raise NotImplementedError

    def CommentsSave(self, com):
        raise NotImplementedError

    def EntriesSimilar(self, entry):
        counts = {}
        entries = {}
        for tag in entry.tags:
            tagged_entries = self.EntriesPublicWithTag(tag, 1000, 0)
            for e in tagged_entries:
                if e.key in counts:
                    counts[e.key] += 1
                else:
                    counts[e.key] = 1
                    entries[e.key] = e
        res = [None, None, None]
        cnt = [0, 0, 0]
        for key in counts:
            if key == entry.key:
                continue
            k = counts[key]
            for i in range(0, 3):
                if res[i] is None:
                    res[i] = key
                    cnt[i] = k
                    break
                elif k > cnt[i]:
                    key_tmp = res[i]
                    k_tmp = cnt[i]
                    res[i] = key
                    cnt[i] = k
                    key = key_tmp
                    k = k_tmp
        for i in range(2, -1, -1):
            if res[i] is None:
                del res[i]
        return [entries[key] for key in res]
