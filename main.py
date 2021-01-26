# coding=UTF-8

from datetime import datetime
import time
import os
import sqlite3

import tornado.ioloop
import tornado.web

import sqlite
from blog import *


def DatetimeToTimestamp(ts):
    return time.mktime(ts.timetuple())


def CreateSqliteConn(db_path):
    sqlite3.register_adapter(datetime, DatetimeToTimestamp)
    conn = sqlite3.connect(db_path)
    try:
        sqlite.CreateTables(conn)
    except:
        pass
    return conn


def SetupServer(db):
    handlers = [
        # LAST.FM
        # (r'/lastfm/api/toptracks$', TopTracksHandler),
        # (r'/lastfm/api/topalbums$', TopAlbumsHandler),
        # (r'/lastfm/api/topartists$', TopArtistsHandler),
        # (r'/lastfm$', LastFMHandler),
        # BLOG
        (r"/import_json$", ImportJsonHandler),
        (r"/import$", ImportHandler),
        (r"/edit/([^/]+)$", EditHandler),
        (r"/edit$", NewEntryHandler),
        (r"/feed$", AtomHandler),
        (r"/rss$", RSSHandler),
        (r"/tag/(.+)/page/(\d+)$", TagHandler),
        (r"/tag/(.+)$", TagHandler),
        (r"/page/(\d+)$", MainHandler),
        (r"/(\d{4})/(\d{2})/page/(\d+)$", ArchiveHandler),
        (r"/(\d{4})/(\d{2})$", ArchiveHandler),
        (r"/([^/]+)/post_comment$", PostComment),
        (r"/([^/]+)$", EntryHandler),
        (r"/$", MainHandler),
    ]
    settings = dict(
        blog_title=u"blog title",
        blog_author=u"blog author",
        author_email="admin@admin.com",
        hub="http://pubsubhubbub.appspot.com",
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        cookie_secret="your secret key",
        months=(
            u"იანვარი",
            u"თებერვალი",
            u"მარტი",
            u"აპრილი",
            u"მაისი",
            u"ივნისი",
            u"ივლისი",
            u"აგვისტო",
            u"სექტემბერი",
            u"ოქტომბერი",
            u"ნოემბერი",
            u"დეკემბერი",
        ),
        blogger_id="8574388056364017758",
        lastfm_api_key="your api key",
        lastfm_user="lastfm username",
        debug=True,
        db=db,
    )
    return tornado.web.Application(handlers, **settings)


def Main():
    conn = CreateSqliteConn("socialme.db")
    app = SetupServer(sqlite.DB(conn))
    app.listen(8081)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    Main()
