﻿import os
import wsgiref.handlers
from tornado.wsgi import WSGIApplication

from blog import *
from lastfm import *

if __name__ == "__main__":
	handlers = [
		# LAST.FM
		(r'/lastfm/api/toptracks$', TopTracksHandler),
		(r'/lastfm/api/topalbums$', TopAlbumsHandler),
		(r'/lastfm/api/topartists$', TopArtistsHandler),
		(r'/lastfm$', LastFMHandler),
	
		# BLOG
		(r'/admin/ping_hub$', PingHubHandler),
		(r'/admin/new_comment$', NewCommentNotificationHandler),
		
		(r'/import$', ImportHandler),
		(r'/edit/([^/]+)$', EditHandler),
		(r'/edit$', NewEntryHandler),
		(r'/feed$', AtomHandler),
		(r'/rss$', RSSHandler),
		(r'/tag/(.+)/page/(\d+)$', TagHandler),
		(r'/tag/(.+)$', TagHandler),
		(r'/page/(\d+)$', MainHandler),
		(r'/(\d{4})/(\d{2})/page/(\d+)$', ArchiveHandler),
		(r'/(\d{4})/(\d{2})$', ArchiveHandler),
		(r'/([^/]+)/post_comment$', PostComment),
		(r'/([^/]+)$', EntryHandler),
		(r'/$', MainHandler),
	]
	
	settings = dict(
		blog_title = u'blog title',
		blog_author = u'blog author',
		author_email = 'admin@admin.com',
		
		hub = 'http://pubsubhubbub.appspot.com',
		
		static_path = os.path.join(os.path.dirname(__file__), 'static'),
		template_path = os.path.join(os.path.dirname(__file__), 'templates'),
		
		cookie_secret = 'your secret key',
		
		months = (u'იანვარი', u'თებერვალი', u'მარტი', u'აპრილი', u'მაისი', u'ივნისი', u'ივლისი', u'აგვისტო', u'სექტემბერი', u'ოქტომბერი', u'ნოემბერი', u'დეკემბერი'),
		
		blogger_id = '8574388056364017758',
		
		lastfm_api_key = 'your api key',
		debug = True,
	)
	
	application = WSGIApplication(handlers, **settings)
	
	wsgiref.handlers.CGIHandler().run(application)