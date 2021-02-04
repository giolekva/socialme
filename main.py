# coding=UTF-8

import time
import os

import git
import tornado.ioloop
import tornado.web

from blog import *
import dbgit
import sqlite


def SetupServer(db):
    handlers = [
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
        debug=True,
        db=db,
    )
    return tornado.web.Application(handlers, **settings)


def Main():
    db = dbgit.GitDB(git.Repo("/Users/lekva/dev/src/b"), sqlite.OpenDB(":memory:"))
    app = SetupServer(db)
    app.listen(8081)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    Main()
