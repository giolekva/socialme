import logging as log
import re
import hashlib
from datetime import datetime, date
from xml import sax

from tornado import web

from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.api import xmpp
from google.appengine.api import memcache

from models import *
import smileys

from pubsubhubbub_publish import *

def check_has_next_page(entries):
	if len(entries) == 6:
		del entries[5]
		return 1
	else:
		return 0
		
class PingHubHandler(web.RequestHandler):
	def get(self):
		try:
			publish(self.settings['hub'], 'http://%s/feed' % self.request.host)
		except:
			taskqueue.add(url = '/admin/ping_hub', method = 'GET')
		
class NewCommentNotificationHandler(web.RequestHandler):
	def get(self):
		status_code = xmpp.OTHER_ERROR
		try:
			status_code = xmpp.send_message(self.settings['author_email'], u'ბლოგზე დაიწერა ახალი კომენტარი')
		except:
			pass

		if status_code != xmpp.NO_ERROR:
			taskqueue.add(url = '/admin/new_comment', method = 'GET')

class BaseHandler(web.RequestHandler):
	def get_comments(self):
		res = memcache.get('comments')
		if res is None:
			res = self.render_string('last_comments.html', comments = Comment.all().order('-published').fetch(3))
			memcache.set('comments', res)
		return res
		
	def recalc_comments(self):
		memcache.set('comments', self.render_string('last_comments.html', comments = Comment.all().order('-published').fetch(3)))
		
	def get_tags(self):
		res = memcache.get('tags')
		if res is None:
			res = self.render_string('tag_cloud.html', tags = Tag.all())
			memcache.set('tags', res)
		return res
		
	def recalc_tags(self):
		memcache.set('tags', self.render_string('tag_cloud.html', tags = Tag.all()))
		
	def get_archive(self):
		res = memcache.get('archive')
		if res is None:
			res = self.render_string('archive.html', arch = Archive.all().order('-year').order('-month'))
			memcache.set('archive', res)
		return res
		
	def recalc_archive(self):
		memcache.set('archive', self.render_string('archive.html', arch = Archive.all().order('-year').order('-month')))
		
	def make_smile(self, text):
		return smileys.make_smile(text)
		
	def paragraphs(self, text):
		pattern = re.compile(r'^\s*(?P<line>.*?)\s*$', re.S | re.M | re.X)
		return pattern.sub('<p>\g<line></p>', text)
	
class MainHandler(BaseHandler):
	def get(self, page = 1):
		page = int(page)
		blogs = Entry.all().filter('is_public =', True).order('-published_time').fetch(6, 5*(page-1))
		has_next = check_has_next_page(blogs)
			
		self.render("index.html", blogs = blogs, current_page = page, has_next = has_next, nav_path = '', title = self.settings['blog_title'])
		
class TagHandler(BaseHandler):
	def get(self, tag, page = 1):
		page = int(page)
		blogs = [cat.parent() for cat in Categories.all().filter('tags =', tag).filter('is_public =', True).order('-published_time').fetch(6, 5*(page-1))]
		has_next = check_has_next_page(blogs)
			
		self.render("index.html", blogs = blogs, current_page = page, has_next = has_next, req_tag = tag, nav_path = '/tag/%s' % tag, title = tag)
	
class ArchiveHandler(BaseHandler):
	def get(self, year, month, page = 1):
		year = int(year)
		month = int(month)
		page = int(page)
		
		next_year = year
		next_month = month
		next_month += 1
		if next_month == 13:
			next_month = 1
			next_year += 1
			
		now = date(year = year, month = month, day = 1)
		next = date(year = next_year, month = next_month, day = 1)
		
		blogs = Entry.all().filter('published_time >=', now).filter('published_time <', next).filter('is_public =', True).order('-published_time').fetch(6, 5*(page-1))
		has_next = check_has_next_page(blogs)
		
		title = 'არქივი %d %s' % (year, self.settings['months'][int(month)-1].encode('utf-8'))
			
		if month < 10:
			month = '0'+str(month)
		else:
			month = str(month)
			
		self.render("index.html", blogs = blogs, current_page = page, has_next = has_next, nav_path = '/%d/%s' % (year, month), title = title)

def generate_threaded_comments(comment, d = 0):
	thread = [{'comment': comment, 'dif': d}]
	
	for com in comment.child_comments.order('published').fetch(1000):
		t = generate_threaded_comments(com, d+20)
		for item in t:
			thread.append(item)
			
	return thread
		
class EntryHandler(BaseHandler):
	def get(self, slug):
		blog = Entry.all().filter('slug =', slug).get()
		if blog is None:
			raise web.HTTPError(404)
		else:
			id = self.get_cookie('whoami')
			
			name = ''
			link = 'http://'
			email = ''
			email_md5 = ''
			
			if id is not None:
				c = Comment.get(id)
				if c is not None:
					name = c.name
					link = c.link
					email = c.email
					email_md5 = c.email_md5
					
			if link == '' or link is None:
				link = 'http://'
				
			comments = []
			for comment in blog.comments.order('published'):
				if comment.parent_comment is None:
					thread = generate_threaded_comments(comment)
					for item in thread:
						comments.append(item)
			
			self.render('post.html', blog = blog, name = name, link = link, email = email, email_md5 = email_md5, comments = comments)
						
class PostComment(BaseHandler):
	def post(self, slug):
		blog = Entry.all().filter('slug =', slug).get()
		if blog is None:
			raise web.HTTPError(404)
		else:
			name = self.get_argument('name', None)
			link = self.get_argument('link', None)
			email = self.get_argument('email', None)
			comm = self.get_argument('comment', None)
			parent_comment = self.get_argument('parent_comment', None)
			honypot = self.get_argument('honypot', None)
			
			if honypot is not None:
				raise web.HTTPError(403)
			
			m = hashlib.md5()
			m.update(email)
			email_md5 = m.hexdigest()
			
			if name is None or email is None or comm is None:
				self.redirect('/%s' % blog.slug)
				return
				
			if link == 'http://':
				link = ''
						
			if parent_comment is None:
				comment = Comment(entry = blog, name = name, link = link, email = email, email_md5 = email_md5, comment = comm, parent_comment = None)
			else:
				comment = Comment(entry = blog, name = name, link = link, email = email, email_md5 = email_md5, comment = comm, parent_comment = db.get(parent_comment).key())
				
			comment.put()
			blog.comments_count += 1
			blog.put()
			self.set_cookie('whoami', str(comment.key()))
			
			taskqueue.add(url = '/admin/new_comment', method = 'GET')
			self.recalc_comments()
			
			self.redirect('/%s' % blog.slug)
			
def new_entry(title, slug, body, tags, published = datetime.now(), updated = datetime.now(), is_public = True, was_public = True):
	slug = slug.replace(' ', '-')
	blog = Entry(title = title, slug = slug, body = body, published_time = published, updated = updated, comments_count = 0, is_public = is_public, was_public = was_public)

	for tag in tags:
		t = Tag.all().filter('name =', tag).get()
		if t is None:
			t = Tag(name = tag, count = 1)
		else:
			t.count = t.count+1
		t.put()		
	
	blog.put()
	Categories(parent = blog, tags = tags, published_time = published, is_public = is_public).put()
	
	year, month = (published.year, published.month)
	archive = Archive.all().filter('year =', year).filter('month =', month).get()
	if archive is None:
		archive = Archive(year = year, month = month, count = 1)
	else:
		archive.count = archive.count+1
	archive.put()
	
	return blog
				
class EditHandler(BaseHandler):
	def get(self, slug):
		blog = Entry.all().filter('slug =', slug).get()
		self.render('edit.html', blog = blog, edit_path = '/edit/%s' % slug)
		
	def post(self, slug):
		body = self.get_argument('body')
		title = self.get_argument('title')
		blog = Entry.all().filter('slug =', slug).get()
		
		was_public = blog.was_public
		
		blog.body = body
		blog.title = title
		if self.get_argument('save', None):
			blog.is_public = False
		else:
			if not blog.was_public:
				blog.published = datetime.now()
			blog.is_public = True
			blog.was_public = True
		
		blog.put()
		
		cat = Categories.all().ancestor(blog).get()
		cat.is_public = blog.is_public
		cat.put()
		
		if was_public:
			taskqueue.add(url = '/admin/ping_hub', method = 'GET')
			
		self.recalc_archive()
		self.recalc_tags()
		
		self.redirect('/%s' % blog.slug)
		
class NewEntryHandler(BaseHandler):
	def get(self):
		self.render('edit.html', blog = Entry(body = u'შეცვალე', title = ' ', slug = ' '), edit_path = '/edit')
		
	def post(self):
		title = self.get_argument('title')
		slug = self.get_argument('slug')
		body = self.get_argument('body')
		if self.get_argument('save', None):
			is_public = False
			was_public = False
		else:
			is_public = True
			was_public = True
		tags = [tag.strip(' ') for tag in self.get_argument('tags').split(',')]
		
		blog = new_entry(title, slug, body, tags, is_public = is_public, was_public = was_public)
		
		if is_public:
			taskqueue.add(url = '/admin/ping_hub', method = 'GET')
			
		self.recalc_archive()
		self.recalc_tags()

		self.redirect('/%s' % blog.slug)
		
class AtomHandler(web.RequestHandler):
	def get(self):
		self.set_header("Content-Type", "application/atom+xml")
		
		blogs = Entry.all().order('-published_time').filter('is_public =', True).fetch(10)
			
		self.render("atom.xml", entries = blogs)
		
class RSSHandler(web.RequestHandler):
	def get(self):
		self.set_header("Content-Type", "application/rss+xml")

		blogs = Entry.all().order('-published_time').filter('is_public =', True).fetch(10)

		self.render("rss.xml", entries = blogs)
		
# წასაშლელია, gdata-ს გამოყენება ჯობია

def to_date(s):
	s = s.encode('utf-8')
	pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})\+(\d{2}):(\d{2})')
	match = pattern.match(str(s))
	g = [int(x) for x in match.groups()]
	return datetime(g[0], g[1], g[2], g[3], g[4], g[5], g[6])
		
class CommentsHandler(sax.handler.ContentHandler):
	def __init__(self, blog):
		self.content = ''
		self.email = ''
		self.entry = blog
		
		self.is_entry = 0
		self.is_published = 0
		self.is_content = 0
		self.is_name = 0
		self.is_uri = 0
		
	def startElement(self, name, attrs):
		self.content = ''
		
		if name == 'entry':
			self.is_entry = 1
			self.link = ''
			self.email = 'noemail@blog.com'
		elif name == 'published':
			self.is_published = 1
		elif name == 'content':
			self.is_content = 1
		elif name == 'name':
			self.is_name = 1
		elif name == 'uri':
			self.is_uri = 1
	
	def endElement(self, name):
		if name == 'entry':
			self.is_entry = 0
			
			m = hashlib.md5()
			m.update(self.email)
			email_md5 = m.hexdigest()
			
			com = Comment(entry = self.entry, name = self.name, link = self.link, email = self.email, email_md5 = email_md5, published = self.published, comment = self.comment)
			com.put()
			print 'imported'
		elif name == 'published':
			self.is_published = 0
			if self.is_entry:
				print self.content.encode('utf-8')
				self.published = to_date(self.content)
		elif name == 'content':
			self.is_content = 0
			if self.is_entry:
				self.comment = self.content
		elif name == 'name':
			self.is_name = 0
			if self.is_entry:
				self.name = self.content
		elif name == 'uri':
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
		self.content = ''
		self.is_entry = 0
		self.is_title = 0
		self.is_content = 0
		self.is_category = 0
		self.is_link = 0
		self.is_published = 0
		self.is_updated = 0
		self.link_count = 0
		
	def startElement(self, name, attrs):
		self.content = ''
		
		if name == 'entry':
			self.is_entry = 1
			self.title = ''
			self.body = ''
			self.link_count = 0
			self.tags = []
		elif name == 'title':
			self.is_title = 1
		elif name == 'content':
			self.is_content = 1
		elif name == 'category':
			self.is_category = 1
			self.tags.append(attrs.items()[0][1])
		elif name == 'link':
			self.is_link = 1
			self.link_count += 1
			if self.is_entry and self.link_count == 1:
				self.comments_url = attrs.items()[0][1]
		elif name == 'published':
			self.is_published = 1
		elif name == 'updated':
			self.is_updated = 1
		
	def endElement(self, name):
		if name == 'entry':
			self.is_entry = 0
			blog = new_entry(self.title, self.title, self.body, self.tags, self.published, self.updated, True, True)
			import_comments(self.comments_url, blog)
		elif name == 'title':
			self.is_title = 0
			if self.is_entry:
				self.title = self.content
		elif name == 'content':
			self.is_content = 0
			if self.is_entry:
				self.body = self.content
		elif name == 'category':
			self.is_category = 0
		elif name == 'link':
			self.is_link = 0
		elif name == 'published':
			self.is_published = 0
			if self.is_entry:
				self.published = to_date(self.content)
		elif name == 'updated':
			self.is_updated = 0
			if self.is_entry:
				self.updated = to_date(self.content)
		
	def characters(self, ch):
		self.content += ch
	
class ImportHandler(web.RequestHandler):
	def get(self):
		blogger_id = self.settings['blogger_id']
		import urllib
		f = urllib.urlopen('http://www.blogger.com/feeds/%s/posts/default' % blogger_id)
		sax.parseString(f.read(), EntriesHandler())
		