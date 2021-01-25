from google.appengine.api import urlfetch

from tornado import web, escape

from blog import BaseHandler

# from django.utils import simplejson as json

from xml import sax


class TopTracksParser(sax.handler.ContentHandler):
    def __init__(self, limit, item_name, items):
        self.item_name = item_name
        self.items = items
        self.tag_stack = []
        self.count = 0
        self.limit = limit

    def startElement(self, name, attrs):
        if self.count == self.limit:
            return

        self.content = ""
        self.tag_stack.append(name)

        if name == self.item_name:
            self.item = {"rank": int(attrs.items()[0][1])}
        elif name == "image" and attrs.items()[0][1] == "large":
            self.item["image_url"] = "_"

    def endElement(self, name):
        if self.count == self.limit:
            return

        del self.tag_stack[-1]
        self.content = str(self.content)

        if name == self.item_name:
            self.items.append(self.item)
            self.count += 1
        elif name == "name":
            if "artist" in self.tag_stack:
                self.item["artist_name"] = self.content
            else:
                self.item["name"] = self.content
        elif name == "playcount":
            self.item["play_count"] = int(self.content)
        elif name == "url":
            if "artist" in self.tag_stack:
                self.item["artist_url"] = self.content
            else:
                self.item["url"] = self.content
        elif name == "image":
            if self.item.get("image_url") == "_":
                self.item["image_url"] = self.content

    def characters(self, ch):
        if self.count == self.limit:
            return

        self.content += ch.encode("utf-8")


class TopChartsHandler(web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(TopChartsHandler, self).__init__(*args, **kwargs)

        self.api_key = self.settings["lastfm_api_key"]
        self.user = self.settings["lastfm_user"]
        self.limit = 15

    def get(self):
        period = self.get_argument("period")
        if period is None:
            period = "overall"

        res = urlfetch.fetch(
            url="http://ws.audioscrobbler.com/2.0/?method=%s&user=%s&api_key=%s&period=%s"
            % (self.method, self.user, self.api_key, period)
        )

        if res.status_code == 200:
            items = []
            sax.parseString(
                res.content, TopTracksParser(self.limit, self.item_name, items)
            )

            self.set_header("Content-Type", "application/json")
            self.write(escape.json_encode(items))
        else:
            self.status_code = res.status_code


class TopTracksHandler(TopChartsHandler):
    def __init__(self, *args, **kwargs):
        super(TopTracksHandler, self).__init__(*args, **kwargs)

        self.method = "user.gettoptracks"
        self.item_name = "track"


class TopAlbumsHandler(TopChartsHandler):
    def __init__(self, *args, **kwargs):
        super(TopAlbumsHandler, self).__init__(*args, **kwargs)

        self.method = "user.gettopalbums"
        self.item_name = "album"


class TopArtistsHandler(TopChartsHandler):
    def __init__(self, *args, **kwargs):
        super(TopArtistsHandler, self).__init__(*args, **kwargs)

        self.method = "user.gettopartists"
        self.item_name = "artist"
        self.limit = 16


class LastFMHandler(BaseHandler):
    def get(self):
        self.render("lastfm.html")
