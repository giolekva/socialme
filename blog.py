import re
import hashlib
from datetime import datetime, date
from xml import sax

from tornado import web

from db import *
import smileys


def check_has_next_page(entries):
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

    @property
    def cache(self):
        return self.settings["cache"]

    def get_comments(self):
        res = self.cache.get("comments")
        if res is None:
            res = self.recalc_comments()
        return res

    def recalc_comments(self):
        comments = self.db.Comments(3)
        res = self.render_string("last_comments.html", comments=comments)
        self.cache.set("comments", res)
        return res

    def get_tags(self):
        res = self.cache.get("tags")
        if res is None:
            res = self.recalc_tags()
        return res

    def recalc_tags(self):
        tags = self.db.TagsAll()
        res = self.render_string("tag_cloud.html", tags=tags)
        self.cache.set("tags", res)
        return res

    def get_archive(self):
        res = self.cache.get("archive")
        if res is None:
            res = self.recalc_archive()
        return res

    def recalc_archive(self):
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
        res = self.render_string("archive.html", arch=archive)
        self.cache.set("archive", res)
        return res

    def make_smile(self, text):
        return smileys.make_smile(text)

    def paragraphs(self, text):
        pattern = re.compile(r"^\s*(?P<line>.*?)\s*$", re.S | re.M | re.X)
        return pattern.sub("<p>\g<line></p>", text)


class MainHandler(BaseHandler):
    def get(self, page=1):
        page = int(page)
        entries = self.db.EntriesGetPublic(6, 5 * (page - 1))
        has_next = check_has_next_page(entries)
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
        has_next = check_has_next_page(entries)
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
        now = date(year=year, month=month, day=1)
        next = date(year=next_year, month=next_month, day=1)
        blogs = self.db.EntriesDateRange(now, next, 6, 5 * (page - 1))
        has_next = check_has_next_page(blogs)
        blogs = AugmentWithCommentCounts(blogs, self.db)
        title = "არქივი %d %s" % (
            year,
            self.settings["months"][int(month) - 1].encode("utf-8"),
        )
        if month < 10:
            month = "0" + str(month)
        else:
            month = str(month)
        self.render(
            "index.html",
            blogs=blogs,
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
    def get(self, slug):
        blog = self.db.EntriesGet(slug)
        if blog is None:
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
            comments = self.db.CommentsForEntryWithKey(blog.key)
            blog.comments_count = len(comments)
            comments = GenerateThreadedComments(None, comments)
            self.render(
                "post.html",
                blog=blog,
                name=name,
                link=link,
                email=email,
                email_md5=email_md5,
                comments=comments,
                similar_entries=self.db.EntriesSimilar(blog),
            )


class PostComment(BaseHandler):
    def post(self, slug):
        blog = self.db.EntriesGet(slug)
        if blog is None:
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
            m = hashlib.md5()
            m.update(email)
            email_md5 = m.hexdigest()
            if name is None or email is None or comm is None:
                self.redirect("/%s" % blog.slug)
                return
            if link == "http://" or link == "":
                link = None
            if parent_comment is None:
                comment = Comment(
                    entry=blog,
                    name=name,
                    link=link,
                    email=email,
                    email_md5=email_md5,
                    comment=comm,
                    parent_comment=None,
                )
            else:
                comment = Comment(
                    entry=blog,
                    name=name,
                    link=link,
                    email=email,
                    email_md5=email_md5,
                    comment=comm,
                    parent_comment=self.db.CommentsGet(parent_comment),
                )
            self.db.CommentsSave(comment)
            self.set_cookie("whoami", str(comment.key))
            self.recalc_comments()
            self.redirect("/%s" % blog.slug)


def new_entry(
    db,
    title,
    slug,
    body,
    tags,
    published_time=datetime.now(),
    updated=datetime.now(),
    is_public=True,
    was_public=True,
):
    slug = slug.replace(" ", "-")
    blog = Entry(
        title=title,
        slug=slug,
        body=body,
        tags=tags,
        published_time=published_time,
        updated_time=updated,
        is_public=is_public,
        was_public=was_public,
    )
    db.EntriesSave(blog)
    return blog


class EditHandler(BaseHandler):
    def get(self, slug):
        blog = self.db.EntriesGet(slug)
        AugmentWithCommentCounts([blog], self.db)
        self.render("edit.html", blog=blog, edit_path="/edit/%s" % slug)

    def post(self, slug):
        body = self.get_argument("body")
        title = self.get_argument("title")
        tags = [tag.strip(" ") for tag in self.get_argument("tags").split(",")]
        blog = self.db.EntriesGet(slug)
        was_public = blog.was_public
        blog.body = body
        blog.title = title
        blog.tags = tags
        if self.get_argument("save", None):
            blog.is_public = False
        else:
            if not blog.was_public:
                blog.published_time = datetime.now()
            blog.is_public = True
            blog.was_public = True
        self.db.EntriesSave(blog)
        self.recalc_archive()
        self.recalc_tags()
        self.redirect("/%s" % blog.slug)


class NewEntryHandler(BaseHandler):
    def get(self):
        self.render(
            "edit.html",
            blog=Entry(body=u"შეცვალე", title=" ", slug=" "),
            edit_path="/edit",
        )

    def post(self):
        title = self.get_argument("title")
        slug = self.get_argument("slug")
        body = self.get_argument("body")
        if self.get_argument("save", None):
            is_public = False
            was_public = False
        else:
            is_public = True
            was_public = True
        tags = [tag.strip(" ") for tag in self.get_argument("tags").split(",")]
        blog = new_entry(
            self.db, title, slug, body, tags, is_public=is_public, was_public=was_public
        )
        self.recalc_archive()
        self.recalc_tags()
        self.redirect("/%s" % blog.slug)


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
    def __init__(self, blog):
        self.content = ""
        self.email = ""
        self.entry = blog
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
            m = hashlib.md5()
            m.update(self.email)
            email_md5 = m.hexdigest()
            com = Comment(
                parent=self.entry,
                name=self.name,
                link=self.link,
                email=self.email,
                email_md5=email_md5,
                published_time=self.published_time,
                comment=self.comment,
            )
            com.put()
            print "imported"
        elif name == "published":
            self.is_published = 0
            if self.is_entry:
                print self.content.encode("utf-8")
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


def import_comments(url, blog):
    import urllib

    f = urllib.urlopen(url)
    sax.parseString(f.read(), CommentsHandler(blog))


class EntriesHandler(sax.handler.ContentHandler):
    def __init__(self):
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
            blog = new_entry(
                self.db,
                self.title,
                self.title,
                self.body,
                self.tags,
                self.published_time,
                self.updated,
                True,
                True,
            )
            import_comments(self.comments_url, blog)
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


class ImportHandler(web.RequestHandler):
    def get(self):
        blogger_id = self.settings["blogger_id"]
        import urllib

        f = urllib.urlopen("http://www.blogger.com/feeds/%s/posts/default" % blogger_id)
        sax.parseString(f.read(), EntriesHandler())


class ImportJsonHandler(web.RequestHandler):
    def get(self):
        import json
        from db import Comment
        from datetime import datetime

        entries = None
        with open("articles.json", mode="r") as inp:
            entries = json.loads(inp.read())
        db = self.settings["db"]
        for e in entries:
            pubdate = datetime.strptime(e["PubDate"], "%Y-%m-%dT%H:%M:%SZ")
            entry = new_entry(
                db,
                e["Title"],
                e["Url"][e["Url"].rfind("/") + 1 :],
                e["Content"],
                e["Tags"],
                published_time=pubdate,
                is_public=True,
                was_public=True,
            )
            thread = []
            for c in e["Comments"]:
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
                    published_time=datetime.strptime(
                        c["PubDate"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                )
                db.CommentsSave(comment)
                thread.append({"Comment": comment, "Margin": c["Margin"]})
