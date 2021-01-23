import db

from google.appengine.ext import db as ds


class Entry(ds.Model):
    title = ds.StringProperty(required = True)
    slug = ds.StringProperty(required = True)
    body = ds.TextProperty(required = True)
    comments_count = ds.IntegerProperty()
    published_time = ds.DateTimeProperty(auto_now_add = True)
    updated_time = ds.DateTimeProperty(auto_now = True)
    is_public = ds.BooleanProperty()
    was_public = ds.BooleanProperty()


class Categories(ds.Model):
    tags = ds.StringListProperty()
    is_public = ds.BooleanProperty()
    published_time = ds.DateTimeProperty(auto_now_add = True)


class Tag(ds.Model):
    name = ds.StringProperty(required = True)
    count = ds.IntegerProperty()


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
    r.comments_count = e.comments_count
    r.published_time = e.published_time
    r.updated_time = e.updated_time
    r.is_public = e.is_public
    r.was_public = e.was_public
    return r


def ToCategory(c):
    if c is None:
        return None
    r = db.Categories()
    r.parent = c.parent_key()
    r.key = c.key()
    r.tags = c.tags
    r.is_public = c.is_public
    r.published_time = c.published_time
    return r


def ToTag(t):
    if t is None:
        return None
    r = db.Tag()
    r.key = t.key()
    r.name = t.name
    r.count = t.count
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

    def EntriesGetPublishedTimes(self):
        q = ds.GqlQuery('SELECT published_time FROM Entry WHERE is_public = :1', True)
        return [e.published_time for e in q]

    def EntriesSave(self, entry):
        entry.key = Entry(
            key=entry.key,
            title=entry.title,
            slug=entry.slug,
            body=entry.body,
            comments_count=entry.comments_count,
            published_time=entry.published_time,
            updated_time=entry.updated_time,
            is_public=entry.is_public,
            was_public=entry.was_public
        ).put()

    def CategoriesPublicWithTag(self, tag, count, after=0):
        categories = Categories.all().filter('tags =', tag).filter('is_public =', True).order('-published_time').fetch(count, after)
        return [ToCategory(c) for c in categories]

    def CategoriesForEntryWithKey(self, key):
        return ToCategory(Categories.all().ancestor(key).get())

    def CategoriesSave(self, cat):
        if cat.key is not None:
            cat.key = Categories(
                key=cat.key,
                tags=cat.tags,
                published_time=cat.published_time,
                is_public=cat.is_public
            ).put()
        else:
            cat.key = Categories(
                parent=cat.parent,
                tags=cat.tags,
                published_time=cat.published_time,
                is_public=cat.is_public
            ).put()

    def TagsAll(self):
        return [ToTag(t) for t in Tag.all()]

    def TagsGet(self, tag):
        return ToTag(Tag.all().filter('name =', tag).get())

    def TagsSave(self, tag):
        tag.key = Tag(key=tag.key, name=tag.name, count=tag.count).put()

    def Comments(self, count):
        comments = Comment.all().order('-published').fetch(count)
        return [ToComment(c) for c in comments]

    def CommentsGet(self, key):
        return ToComment(Comment.get(key))

    def CommentsForEntryWithKey(self, key):
        comments = Comment.all().filter("entry = ", key).order('published')
        return [ToComment(c) for c in comments]

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
