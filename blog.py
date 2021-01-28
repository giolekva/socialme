import re
from datetime import datetime, date

from tornado import web

from db import *
import smileys


def CheckHasNextPage(entries):
    if len(entries) == 6:
        del entries[5]
        return 1
    else:
        return 0


def AugmentWithCommentCounts(entries, db):
    for e in entries:
        e.comments_count = db.CommentsCountForEntryWithKey(e.key)
    return entries


class BaseHandler(web.RequestHandler):
    @property
    def db(self):
        return self.settings["db"]

    def get_comments(self):
        comments = self.db.Comments(3)
        return self.render_string("last_comments.html", comments=comments)

    def get_tags(self):
        tags = self.db.TagsAll()
        return self.render_string("tag_cloud.html", tags=tags)

    def get_archive(self):
        published_times = self.db.EntriesGetPublishedTimes()
        counts = {}
        for p in published_times:
            k = (p.year, p.month)
            if k in counts:
                counts[k] += 1
            else:
                counts[k] = 1
        archive = [
            Archive(year=c[0][0], month=c[0][1], count=c[1]) for c in counts.items()
        ]
        archive.sort(reverse=True, key=lambda a: a.year * 12 + a.month)
        return self.render_string("archive.html", arch=archive)

    def make_smile(self, text):
        return smileys.make_smile(text)

    def paragraphs(self, text):
        pattern = re.compile(r"^\s*(?P<line>.*?)\s*$", re.S | re.M | re.X)
        return pattern.sub("<p>\g<line></p>", text)


class MainHandler(BaseHandler):
    def get(self, page=1):
        page = int(page)
        entries = self.db.EntriesGetPublic(6, 5 * (page - 1))
        has_next = CheckHasNextPage(entries)
        entries = AugmentWithCommentCounts(entries, self.db)
        self.render(
            "index.html",
            blogs=entries,
            current_page=page,
            has_next=has_next,
            nav_path="",
            title=self.settings["blog_title"],
        )


class TagHandler(BaseHandler):
    def get(self, tag, page=1):
        page = int(page)
        entries = self.db.EntriesPublicWithTag(tag, 6, 5 * (page - 1))
        has_next = CheckHasNextPage(entries)
        entries = AugmentWithCommentCounts(entries, self.db)
        self.render(
            "index.html",
            blogs=entries,
            current_page=page,
            has_next=has_next,
            req_tag=tag,
            nav_path="/tag/%s" % tag,
            title=tag,
        )


class ArchiveHandler(BaseHandler):
    def get(self, year, month, page=1):
        year = int(year)
        month = int(month)
        page = int(page)
        next_year = year
        next_month = month
        next_month += 1
        if next_month == 13:
            next_month = 1
            next_year += 1
        now = datetime(year=year, month=month, day=1)
        next = datetime(year=next_year, month=next_month, day=1)
        entries = self.db.EntriesDateRange(now, next, 6, 5 * (page - 1))
        has_next = CheckHasNextPage(entries)
        entries = AugmentWithCommentCounts(entries, self.db)
        title = "არქივი %d %s" % (
            year,
            self.settings["months"][int(month) - 1],
        )
        if month < 10:
            month = "0" + str(month)
        else:
            month = str(month)
        self.render(
            "index.html",
            blogs=entries,
            current_page=page,
            has_next=has_next,
            nav_path="/%d/%s" % (year, month),
            title=title,
        )


def GenerateThreadedComments(current, comments, dif=0):
    ret = []
    if current is not None:
        ret.append({"dif": dif, "comment": current})
    if current is None:
        for c in comments:
            if c.parent_comment is None:
                ret.extend(GenerateThreadedComments(c, comments, dif))
    else:
        for c in comments:
            if c.parent_comment is not None and c.parent_comment.key == current.key:
                ret.extend(GenerateThreadedComments(c, comments, dif + 20))
    return ret


class EntryHandler(BaseHandler):
    def get(self, key):
        entry = self.db.EntriesGet(key)
        if entry is None:
            raise web.HTTPError(404)
        else:
            id = self.get_cookie("whoami")
            name = ""
            link = "http://"
            email = ""
            email_md5 = ""
            if id is not None:
                c = self.db.CommentsGet(id)
                if c is not None:
                    name = c.name
                    link = c.link
                    email = c.email
                    email_md5 = c.email_md5
            if link == "" or link is None:
                link = "http://"
            comments = self.db.CommentsForEntryWithKey(entry.key)
            entry.comments_count = len(comments)
            comments = GenerateThreadedComments(None, comments)
            self.render(
                "post.html",
                blog=entry,
                name=name,
                link=link,
                email=email,
                email_md5=email_md5,
                comments=comments,
                similar_entries=self.db.EntriesSimilar(entry),
            )


class PostComment(BaseHandler):
    def post(self, key):
        entry = self.db.EntriesGet(key)
        if entry is None:
            raise web.HTTPError(404)
        else:
            name = self.get_argument("name", None)
            link = self.get_argument("link", None)
            email = self.get_argument("email", None)
            comm = self.get_argument("comment", None)
            parent_comment = self.get_argument("parent_comment", None)
            honypot = self.get_argument("honypot", None)
            if honypot is not None:
                raise web.HTTPError(403)
            if name is None or email is None or comm is None:
                self.redirect("/%s" % entry.key)
                return
            if link == "http://" or link == "":
                link = None
            if parent_comment is None:
                comment = Comment(
                    entry=entry,
                    name=name,
                    link=link,
                    email=email,
                    comment=comm,
                    parent_comment=None,
                )
            else:
                comment = Comment(
                    entry=entry,
                    name=name,
                    link=link,
                    email=email,
                    comment=comm,
                    parent_comment=self.db.CommentsGet(parent_comment),
                )
            self.db.CommentsSave(comment)
            self.set_cookie("whoami", str(comment.key))
            self.redirect("/%s" % entry.key)


class EditHandler(BaseHandler):
    def get(self, key):
        entry = self.db.EntriesGet(key)
        AugmentWithCommentCounts([entry], self.db)
        self.render("edit.html", blog=entry, edit_path="/edit/%s" % key)

    def post(self, key):
        body = self.get_argument("body")
        title = self.get_argument("title")
        tags = [tag.strip(" ") for tag in self.get_argument("tags").split(",")]
        entry = self.db.EntriesGet(key)
        was_public = entry.was_public
        entry.body = body
        entry.title = title
        entry.tags = tags
        if self.get_argument("save", None):
            entry.is_public = False
        else:
            if not entry.was_public:
                entry.published_time = datetime.now()
            entry.is_public = True
            entry.was_public = True
        self.db.EntriesSave(entry)
        self.redirect("/%s" % entry.key)


class NewEntryHandler(BaseHandler):
    def get(self):
        self.render(
            "edit.html",
            blog=Entry(body=u"შეცვალე", title=" ", key=" "),
            edit_path="/edit",
        )

    def post(self):
        title = self.get_argument("title")
        key = self.get_argument("key").replace(" ", "-")
        body = self.get_argument("body")
        if self.get_argument("save", None):
            is_public = False
            was_public = False
        else:
            is_public = True
            was_public = True
        tags = [tag.strip(" ") for tag in self.get_argument("tags").split(",")]
        now = datetime.now()
        entry = Entry(
            key=key,
            title=tile,
            body=body,
            tags=tags,
            published_time=now,
            updated_time=now,
            is_public=is_public,
            was_public=was_public,
        )
        self.db.EntriesSave(entry)
        self.redirect("/%s" % entry.key)


class AtomHandler(web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/atom+xml")
        db = self.settings["db"]
        entries = AugmentWithCommentCounts(db.EntriesGetPublic(10), db)
        self.render("atom.xml", entries=entries)


class RSSHandler(web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/rss+xml")
        db = self.settings["db"]
        entries = AugmentWithCommentCounts(db.EntriesGetPublic(10), db)
        self.render("rss.xml", entries=entries)
