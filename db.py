import re

class Entry(object):
    def __init__(self, key=None, title=None, slug=None, body=None, tags=None, published_time=None, updated_time=None, is_public=None, was_public=None):
        self.key = key
        self.title = title
        self.slug = slug
        self.body = body
        self.tags = tags
        self.published_time = published_time
        self.updated_time = updated_time
        self.is_public = is_public
        self.was_public = was_public

    def get_paragraphs(self):
	pattern = re.compile(r'^\s*(?P<line>.*?)\s*$', re.S | re.M | re.X)
	return pattern.sub('<p>\g<line></p>', self.body)


class Tag(object):
    def __init__(self, key=None, name=None, count=None):
        self.key = key
	self.name = name
	self.count = count


class Comment(object):
    def __init__(self, key=None, entry=None, name=None, link=None, email=None, email_md5=None, comment=None, parent_comment=None, published=None):
        self.key = key
	self.entry = entry
	self.name = name
	self.link = link
	self.email = email
	self.email_md5 = email_md5
	self.comment = comment
	self.parent_comment = parent_comment
	self.published = published

    def __repr__(self):
        ret = "{" + str(self.key)
        if self.parent_comment:
            ret +=" , " + str(self.parent_comment.key)
        ret += "}"
        return ret

    def __str__(self):
        return self.__repr__()


class DB(object):
    def EntriesGet(self, slug):
        raise NotImplementedError

    def EntriesGetWithKey(self, key):
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

    def TagsAll(self):
        raise NotImplementedError

    def TagsGet(self, name):
        raise NotImplementedError

    def TagsSave(self, tag):
        raise NotImplementedError

    def Comments(self, count):
        raise NotImplementedError

    def CommentsGet(self, id):
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
