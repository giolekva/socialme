import re

from google.appengine.ext import db

class Entry(db.Model):
	title = db.StringProperty(required = True)
	slug = db.StringProperty(required = True)
	body = db.TextProperty(required = True)
	comments_count = db.IntegerProperty()
	published_time = db.DateTimeProperty(auto_now_add = True)
	updated_time = db.DateTimeProperty(auto_now = True)
	is_public = db.BooleanProperty()
	was_public = db.BooleanProperty()
	
	def tags(self):
		return Categories.all().ancestor(self).get().tags
		
	def get_paragraphs(self):
		pattern = re.compile(r'^\s*(?P<line>.*?)\s*$', re.S | re.M | re.X)
		return pattern.sub('<p>\g<line></p>', self.body)
		
	def similar_entries(self):
		if hasattr(self, 'similars'):
			return self.similars
			
		tags = self.tags()
		entries = {}
		
		for tag in tags:
			keys = Categories.all(keys_only = True).filter('tags =', tag).fetch(1000)
			for key in keys:
				if key in entries:
					cnt = entries[key] + 1
				else:
					cnt = 1
					
				entries[key] = cnt
				
		res = [None, None, None]
		cnt = [0, 0, 0]
				
		for key in entries:
			if key.parent() == self.key():
				continue
				
			k = entries[key]
			
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
				
		self.similars = [Entry.get(key.parent()) for key in res]
		return self.similars
					
class Categories(db.Model):
	tags = db.StringListProperty()
	is_public = db.BooleanProperty()
	published_time = db.DateTimeProperty(auto_now_add = True)
	
class Tag(db.Model):
	name = db.StringProperty(required = True)
	count = db.IntegerProperty()
	
class Comment(db.Model):
	entry = db.ReferenceProperty(Entry, collection_name = 'comments')
	name = db.StringProperty(required = True)
	link = db.LinkProperty(required = False)
	email = db.EmailProperty(required = True)
	email_md5 = db.StringProperty(required = True)
	comment = db.TextProperty(required = True)
	parent_comment = db.SelfReferenceProperty(required = False, collection_name = 'child_comments')
	published = db.DateTimeProperty(auto_now_add = True)
	
class Archive(db.Model):
	year = db.IntegerProperty(required = True)
	month = db.IntegerProperty(required = True)
	count = db.IntegerProperty()