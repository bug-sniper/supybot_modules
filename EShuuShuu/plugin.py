###
# Copyright (c) 2014, Steven Bluen
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import urllib2
import re

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.conf import supybot


class EShuuShuu(callbacks.Plugin, plugins.ChannelDBHandler):
    """Returns images from e-shuushuu"""

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)

        self.indexdict = {}
        self.tagids = {}

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            db.text_factory = str
            return db
        db = sqlite3.connect(filename)
        db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE tagpos (
                            id INTEGER PRIMARY KEY,
                            tag TEXT,
                            recentid INTEGER,
                            recentpage INTEGER
                          )""")
        db.commit()
        return db

    def search(self, irc, msg, args, channel, query):
        """Searches for a picture from e-shuushuu.

        Query should be written in danbooru format:
        Spaces should be replaced with underscores. Tags should be separated 
        by a space. Negation is done by preceding with a -."""

        if not query:
            query=""
        query = query.replace("_", "%20")
        query = query.replace("!", "-")
        
        #First, the tag ids must be discovered if there are any.
        ids = []
        negations = [] #boolean array representing whether a tag is negated
        urltemplate1 = ("http://e-shuushuu.net/tags/" + 
            "?tag_name={}&type={}&show_aliases=0")
        tags = query.split()

        if len(tags)>0:

            for i in range(len(tags)):
                #accept either a ! or a - for the negation prefix
                negations.append(tags[i][0] == "-")
                if negations[i]:
                    #remove the prefix now that it has been accounted for
                    tags[i] = tags[i][1:]
            for tag in tags:
                if tag in self.tagids:
                    #already cached
                    ids.append(self.tagids[tag])
                    continue
                for i in [2, 1, 0, 3]:
                    #i+1 because the website menu is 1-indexed
                    url1 = urltemplate1.format(tag, i+1)
                    self.log.info("looking up on " +url1)
                    f = urllib2.urlopen(url1)
                    pattern = ('<li><a href="/tags/([0-9]*)">' +
                        '.*?</a></li>')
                    matches = re.findall(pattern, f.read())
                    #Note that match 0 is part of the layout and should be
                    #excluded from this.
                    if len(matches)>1:
                        ids.append(matches[1])
                        self.tagids[tag] = matches[1]
                        break

            if len(tags) != len(ids):
                irc.reply("Some of those tags are not present.")
                return
            assert len(tags) == len(ids) == len(negations)
            
            param = "+".join(["!"+ids[i] if negations[i] else ids[i]
                for i in range(len(tags))])
            urltemplate2 = ("http://e-shuushuu.net/search/results/" + 
                "?page={}&tags=" + param)
            
        else:
            #when no tags are entered, use this
            urltemplate2 = "http://e-shuushuu.net/?page={}"
        
        #Next, we need to find the post ids.
        pattern = '<a href="/image/[0-9]*/">Image #([0-9]*)</a>'

        #TODO: allow searching though other pages
        page = 1
        url2 = urltemplate2.format(page)
        self.log.info("looking for post tags on " +url2)
        pageids = re.findall(pattern, urllib2.urlopen(url2).read())
        if len(pageids) == 0:
            irc.reply("no results found for entered query")
            return
        
        #Next, we get the picture's link.
        if query not in self.indexdict:
            #It starts at 0.
            self.indexdict[query] = 0
        else:
            #It goes back to the start at the end of a page of 10.
            self.indexdict[query] = (self.indexdict[query] + 1) % 10
            if self.indexdict[query] >= len(pageids):
                #needed to avoid going out of range
                self.indexdict[query] = 0;
        index = self.indexdict[query]
            
        url3 = "http://e-shuushuu.net/image/{}".format(pageids[index])
        
        #Next, we get the tags for that image and post both to the channel.
        self.log.info("looking for information on " +url3)
        pattern = '"<a href="/tags/[0-9]+">(.*?)</a>"'
        text = urllib2.urlopen(url3).read()
        tags = re.findall(pattern, text)
        pattern =('thumb_image" href="' +
                  '(/images/[0-9]+-[0-9]+-[0-9]+-[0-9]+\\.[a-z]+)')
        imageurl = "http://e-shuushuu.net" + re.search(
            pattern, text).groups()[0]
        output = imageurl + " " + ", ".join(tags)
        irc.reply(output, prefixNick=False)

    search = wrap(search, ['channel', additional('text')])

Class = EShuuShuu


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
