import db

from google.appengine.ext import db as ds


class Entry(ds.Model):
    title = ds.StringProperty(required = True)
    slug = ds.StringProperty(required = True)
    body = ds.TextProperty(required = True)
    tags = ds.StringListProperty()
    published_time = ds.DateTimeProperty(auto_now_add = True)
    updated_time = ds.DateTimeProperty(auto_now = True)
    is_public = ds.BooleanProperty()
    was_public = ds.BooleanProperty()


class Comment(ds.Model):
    entry = ds.ReferenceProperty(Entry, collection_name = 'comments')
    name = ds.StringProperty(required = True)
    link = ds.LinkProperty(required = False)
    email = ds.EmailProperty(required = True)
    email_md5 = ds.StringProperty(required = True)
    comment = ds.TextProperty(required = True)
    parent_comment = ds.SelfReferenceProperty(required = False, collection_name = 'child_comments')
    published = ds.DateTimeProperty(auto_now_add = True)


def ToEntry(e):
    if e is None:
        return None
    r = db.Entry()
    r.key = e.key()
    r.title = e.title
    r.slug = e.slug
    r.body = e.body
    r.tags = e.tags
    r.published_time = e.published_time
    r.updated_time = e.updated_time
    r.is_public = e.is_public
    r.was_public = e.was_public
    return r


def ToComment(c):
    if c is None:
        return None
    r = db.Comment()
    r.key = c.key()
    r.entry = c.entry
    r.name = c.name
    r.link = c.link
    r.email = c.email
    r.email_md5 = c.email_md5
    r.comment = c.comment
    if c.parent_comment:
        r.parent_comment = ToComment(c.parent_comment)
    r.published = c.published
    return r


class Datastore(db.DB):
    def EntriesGet(self, slug):
        return ToEntry(Entry.all().filter('slug =', slug).get())

    def EntriesGetWithKey(self, key):
        return ToEntry(Entry.get(key))

    def EntriesGetPublic(self, count, after=0):
        entries = Entry.all().filter('is_public =', True).order('-published_time').fetch(count, after)
        return [ToEntry(e) for e in entries]

    def EntriesDateRange(self, begin, end, count, after=0):
        entries = Entry.all().filter('published_time >=', begin).filter('published_time <', end).filter('is_public =', True).order('-published_time').fetch(count, after)
        return [ToEntry(e) for e in entries]

    def EntriesPublicWithTag(self, tag, count, after=0):
        entries = Entry.all().filter('tags =', tag).filter('is_public =', True).order('-published_time').fetch(count, after)
        return [ToEntry(e) for e in entries]

    def EntriesGetPublishedTimes(self):
        q = ds.GqlQuery('SELECT published_time FROM Entry WHERE is_public = :1', True)
        return [e.published_time for e in q]

    def EntriesSave(self, entry):
        entry.key = Entry(
            key=entry.key,
            title=entry.title,
            slug=entry.slug,
            body=entry.body,
            tags=entry.tags,
            published_time=entry.published_time,
            updated_time=entry.updated_time,
            is_public=entry.is_public,
            was_public=entry.was_public
        ).put()

    def TagsAll(self):
        q = ds.GqlQuery('SELECT tags FROM Entry WHERE is_public = :1', True)
        counts = {}
        for entry in q:
            for tag in entry.tags:
                if tag in counts:
                    counts[tag] += 1
                else:
                    counts[tag] = 1
        return [db.Tag(tag, count) for (tag, count) in counts.items()]

    def Comments(self, count):
        comments = Comment.all().order('-published').fetch(count)
        return [ToComment(c) for c in comments]

    def CommentsGet(self, key):
        return ToComment(Comment.get(key))

    def CommentsForEntryWithKey(self, key):
        comments = Comment.all().filter("entry = ", key).order('published')
        return [ToComment(c) for c in comments]

    def CommentsCountForEntryWithKey(self, key):
        comments = Comment.all(keys_only=True).filter("entry = ", key)
        ret = 0
        for _ in comments:
            ret += 1
        return ret

    def CommentsSave(self, com):
        parent_comment_key = None
        if com.parent_comment:
            parent_comment_key = com.parent_comment.key
        if com.published:
            com.key = Comment(
                key=com.key,
                entry=com.entry.key,
                name=com.name,
                link=com.link,
                email=com.email,
                email_md5=com.email_md5,
                comment=com.comment,
                parent_comment=parent_comment_key,
                published=com.published
            ).put()
        else:
            com.key = Comment(
                key=com.key,
                entry=com.entry.key,
                name=com.name,
                link=com.link,
                email=com.email,
                email_md5=com.email_md5,
                comment=com.comment,
                parent_comment=parent_comment_key,
            ).put()
