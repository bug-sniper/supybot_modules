###
# Copyright (c) 2013, Steven
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
import os
import time
import random
import inflect
import re

#open is by default overshadowed by the imports
_open=open
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.conf import supybot

try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

#colors
foodnamecolor="12"
oc="12"
dc="3"
mc="7"
tc="5"
pc="4"
ic="15"

#+ means that the message is newer and should appear twice as frequently
#* means that "you " must precede the message
commonprobs = ["allowed the plastic wrapping to melt into the food",
                "sneezed onto the food",
                "woke up at a hospital before you could finish the job",
                "*falling meteorites made huge crators in the food",
                "*the dough expanded too fast and you threw the food away",
                "*the food grew wings and flew away",
                "*the food grew legs and ran away",
                "+*the food became emo and cut itself into pieces",
                "+*squirrels with pickaxes broke in and ate the food",
                "+*a Federation starship beamed the food away to check for " +
                "contraband",
                "+*ninjas stole the food and left an illegible ransom note",
                "+*someone wrote \"mv * /dev/null\" and the food was never" +
                " seen again",
                "+*the oven union went on strike and refused to help you",
                "+*you multiplied by 0 and the food disappeared",
                "+*the food molecules spontaneously converged onto a single" +
                " space-time point and imploded into a black hole",
                "+*the food moved through the 5th dimension and travelled"
                " in a direction you are unable to walk in",
                "+*the IRS took the food as a civil asset forfeiture",
                "*the food somehow timetravelled 50 years into the {}".format(
                    random.choice(("past", "future")))
           ]
#+ means to double the change of this problem happening relative to the others
temp = [i for i in commonprobs if i[0] == "+"]
commonprobs += temp
commonprobs = [i[1:] if i[0] == "+" else i for i in commonprobs]
    
def _is_determiner(string):
    determiners = ['the', 'a', 'an', 'another', 'no', 'the', 'a', 'an',
                    'no', 'another', 'some', 'any', 'my', 'our', 'their',
                    'her', 'his', 'its', 'another', 'no', 'each', 'every',
                    'certain', 'its', 'another', 'no', 'this', 'that',
                    'all']

    if string in determiners:
        return True
    elif string[-2:] == "'s":
        return True
    #any and __builtins__ are overshadowed
    #elif __builtins__.any(c.isdigit() for c in string):
    elif len([c for c in string if c in "1234567890"]) > 0:
        return True
    else:
        return False

class BakeIt(callbacks.Plugin, plugins.ChannelDBHandler):
    """bake [food]: bakes a food and adds it to the database
    eat [username]: consumes a food to remove it from the database"""

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)
        exec open("plugins/BakeIt/foods.txt", "r").read()
        exec open("plugins/BakeIt/goods.txt", "r").read()

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            db.text_factory = str
            return db
        db = sqlite3.connect(filename)
        db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE foods (
                          id INTEGER PRIMARY KEY,
                          foodname TEXT,
                          added_at TIMESTAMP,
                          baker TEXT,
                          quality TEXT,
                          eater TEXT,
                          verb TEXT
                          )""")
        cursor.execute("""CREATE TABLE bakers (
                          id INTEGER PRIMARY KEY,
                          username TEXT UNIQUE ON CONFLICT REPLACE
                          )""")
        db.commit()
        return db

    def bake(self, irc, msg, args, channel, foodname):
        """[food]: bakes a food and adds it to the database.
    
        A randomly selected default food choice is selected if one is not
        provided."""
        db = self.getDb(channel)
        cursor = db.cursor()
        p=inflect.engine()
        
        username = msg.nick
        
        if not foodname:
            foodname = random.choice(self.goods)
            capitals = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            lowers = "abcdefghijklmnopqrstuvwxyz"
            #if there is only one capitalized letter in the food name
            if len([c for c in foodname if c in capitals])  == 1:
                #if it is the first letter
                if foodname[0] in capitals:
                    #lowercase it
                    foodname = (lowers[capitals.index(foodname[0])] 
                                + foodname[1:])
                
            
        foodname = foodname.strip()
            
        #Start the food name with "a" or "an" if it is singular
        #and this ins't already done.
        if p.singular_noun(foodname):
            plural=True
        else:
            if not _is_determiner(foodname.split()[0]):
                foodname = p.a(foodname)
            plural=False

        if random.random()<0.33:
            problems =  [
                "overcooked the dough",
                        ]
            problems += commonprobs
            problem = random.choice(problems)
            if problem[0] == "*":
                response = ("You tried to bake %s%s. Unfortunately, %s."
                            ) % (foodnamecolor, foodname, problem[1:])
            else:
                response = ("You tried to bake %s%s. Unfortunately, " +
                    "you %s and " +
                    "had to discard it.") % (foodnamecolor, foodname, problem)
            irc.reply(response)
            return
        
        response = ("You baked %s%s." % 
        (foodnamecolor, foodname))
        quality = "unknown"
        
        reason = random.choice(("misinterpreted the recipe",
                                "accidentally divided by 0",
                                "used an ogre cookbook",
                                "slid in a copy from a parallel universe"
                                ))        
        if random.random() < 0.33:
            response += (" You somehow %s and baked double portions." %
                         reason)
            cursor.execute("""INSERT INTO foods VALUES
                    (NULL, ?, ?, ?, ?, NULL, 'baked')""",
                    (foodname, int(time.time()), username, quality))
        else:
            response += (" %s quality remains to be seen." %
                         ("Their" if plural else "Its"))
        cursor.execute("""INSERT INTO foods VALUES
                (NULL, ?, ?, ?, ?, NULL, 'cooked')""",
                (foodname, int(time.time()), username, quality))
        cursor.execute("""INSERT INTO bakers VALUES
                    (NULL, ?)""", (username,))
        
        irc.reply(response)
        
        
    bake = wrap(bake, ['channel', additional('text')])
    
    def cook(self, irc, msg, args, channel, foodname):
        """[food]: cooks a food and adds it to the database.
    
        A randomly selected default food choice is selected if one is not
        provided."""
        db = self.getDb(channel)
        cursor = db.cursor()
        p=inflect.engine()
        
        username = msg.nick
        
        if not foodname:
            foodname = random.choice(self.foods)
            capitals = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            lowers = "abcdefghijklmnopqrstuvwxyz"
            #if there is only one capitalized letter in the food name
            if len([c for c in foodname if c in capitals]) == 1:
                #if it is the first letter
                if foodname[0] in capitals:
                    #lowercase it
                    foodname = (lowers[capitals.index(foodname[0])] 
                                + foodname[1:])
                
            
        foodname = foodname.strip()
            
        #Start the food name with "a" or "an" if it is singular
        #and this ins't already done.
        if p.singular_noun(foodname):
            plural=True
        else:
            if not _is_determiner(foodname.split()[0]):
                foodname = p.a(foodname)
            plural=False
        
        if random.random()<0.33:
            if "soup" in foodname or "cream" in foodname:
                problems = ["knocked the soup onto the floor", 
                    "added moldy ingredients to the soup", 
                    "sneezed onto the soup",
                    "woke up at a hospital before you could finish your " +
                    "cooking",
                    "found frogs taking residence in your soup",
                    "*the soup splattered and your time was spent cleaning up",
                    "*the soup evaporated",
                    "*squirrels with pickaxes broke in and ate the soup",
                    "*the soup got sucked up by lizards with straws",
                    "*a Federation starship beamed the soup away to check " +
                    "for contraband",
                    "*ninjas stole the soup and left an illegible ransom " +
                    "note",
                    "*the IRS took your soup as a civil asset forfeiture",
                    "*the soup somehow timetravelled 50 years " +
                    "into the {}".format(
                        random.choice(("past", "future")))
                                         ]
            else:
                problems = [  
                    "cooked the food upside-down"
                    ]
                problems += commonprobs
            problem = random.choice(problems)
                
            if problem[0] == "*":
                response = ("You tried to cook %s%s. Unfortunately, %s."
                            ) % (foodnamecolor, foodname, problem[1:])
            else:
                response = ("You tried to cook %s%s. Unfortunately, " +
                    "you %s and " +
                    "had to discard it") % (foodnamecolor, foodname, problem)
            irc.reply(response)
            return
        
        response = ("You cooked %s%s." % 
        (foodnamecolor, foodname))
        quality = "unknown"
        
        reason = random.choice(["misinterpreted the recipe",
                                "accidentally divided by 0",
                                "used an ogre cookbook"
                                ])        
        if random.random() < 0.33:
            response += (" You somehow %s and cooked double portions." %
                         reason)
            cursor.execute("""INSERT INTO foods VALUES
                    (NULL, ?, ?, ?, ?, NULL, 'cooked')""",
                    (foodname, int(time.time()), username, quality))
        else:
            response += (" %s quality remains to be seen." %
                         ("Their" if plural else "Its"))
        cursor.execute("""INSERT INTO foods VALUES
                (NULL, ?, ?, ?, ?, NULL, 'cooked')""",
                (foodname, int(time.time()), username, quality))
        #not useful to call it the cooks table because that only
        #makes the code more complex
        cursor.execute("""INSERT INTO bakers VALUES
                    (NULL, ?)""", (username,))
        
        
        
        irc.reply(response)
        
        
    cook = wrap(cook, ['channel', additional('text')])

    def eat(self, irc, msg, args, channel, other):
        """[other]: consumes a food to remove it from the database.
    
        Consumes a random food baked by other. If other is not provided,
        a randomly selected food is eaten."""
        db = self.getDb(channel)
        cursor = db.cursor()
        p=inflect.engine()
        
        username = msg.nick
        
        if other:
            pass
            #Taking this part out for now, by popular request.
#             if username.lower() == other.lower():
#                 irc.reply("You can't eat your own food! " + 
#                 "What if you poisoned yourself?!")
#                 return
        else:
            cursor.execute(
                """SELECT baker FROM foods WHERE eater IS NULL""",
                #This part removed by popular request. 
#                 AND LOWER(baker) <> ?""", 
#                 [username.lower()]
            )
            others = [i[0] for i in cursor.fetchall()]
            #If the user selected nobody but there are still no goods
            #made by someone else
            if others == []: 
                irc.reply("There are no goods available for you " + 
                 "to eat. Perhaps try baking something yourself.")
                return
            other = random.choice(others)
            



        cursor.execute("""SELECT * FROM foods WHERE LOWER(baker) = ?
        AND eater IS NULL""", [other.lower()])
        entries = cursor.fetchall()
        
        #If the the person provided in the argument doesn't have anything
        #baked
        if entries == []:
            cursor.execute(
                """SELECT count(*) as cnt FROM bakers WHERE LOWER(username)
                 = ?""", 
                [other.lower()])
            other_has_baked = cursor.fetchone()[0] == (1,)
            #If the user selected someone who has never baked or cooked
            if other_has_baked:
                irc.reply(other + " has never prepared any food. " +
                          "Perhaps you can try cooking or baking" + 
                          " something yourself.")
                return
            
            #If the user selected someone who has baked in the past, but
            #everything made by the person has been eaten
            else:
                irc.reply(other + " does not currently have any foods " +
                          "available for you to eat. Perhaps you " +
                          "can try baking or cooking something yourself.")
                return
        
        selected_entry = random.choice(entries)
        (id, foodname, added_at, baker, unspecified_quality, eater, verb
         ) = selected_entry
        
        timediff = int(time.time()) - added_at
        
        #for the word after "which"
        inflection1 = "were" if p.singular_noun(foodname) else "was"
        
        #for "goods were" or "good was"?
        #no longer used
        #inflection2 = "s were" if p.singular_noun(foodname) else " was"
        
        SECONDS_PER_DAY = 86400.
        SECONDS_PER_HOUR = 3600.
        SECONDS_PER_MINUTE = 60.
        days = int(timediff / SECONDS_PER_DAY)
        hours = int((timediff - SECONDS_PER_DAY*days) / SECONDS_PER_HOUR)
        minutes = int((timediff - (days*SECONDS_PER_DAY) - \
            (hours*SECONDS_PER_HOUR)) / SECONDS_PER_MINUTE)
        seconds = int(timediff % 60)
        timenames = (" day", " hour", " minute", " second")
        timeparts = tuple(str(value) + p.plural(timenames[index], value)
                      for index, value in enumerate((
                          days, hours, minutes, seconds)))
        
        qualities = ("delicious", "mediocre", "trash", "poisoned",
                     "inaccessible")
        quality = random.choice(qualities)
        
        if ("cake" in foodname and
            "real" not in foodname and
            "true" not in foodname):
            #It's a lie.
            quality = "inaccessible"
        
        #override the random decision if specified
        for i in qualities:
            if i in foodname:
                quality = i
        
        if (" for " in foodname and 
            foodname.split(" for ")[-1] in 
            irc.state.channels[channel].users):
            recipient = foodname.split(" for ")[-1]
            if msg.nick == recipient:
                #No point in saying you see yourself make food for yourself.
                recipient = None
        else:
            recipient = None
        
        if quality == "delicious":
            if recipient:
                response = ("You just ate {oc}%s which %s %s by %s about" +
                        " %s, %s, %s, and %s ago. %s regrets not eating the" +
                        " food sooner."
                        ).format(oc=oc, mc=mc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
            else:
                reaction = random.choice(("you wanted to eat more",
                    "you ate every last crumb",
                    "you're sad when it's finished",
                    "you ate it all in one bite",
                    "you ate it very slowly to enjoy it more",
                    "you even ate the dish underneath"))
                
                response = ("You just ate {oc}%s which %s %s by %s about" +
                            " %s, %s, %s, and %s ago." +
                            " The food was {dc}delicious and %s."
                            ).format(oc=oc, dc=dc) % \
                ((foodname, inflection1, verb, other) + 
                 timeparts + (reaction,))
            
            
            cursor.execute("""UPDATE foods SET eater = ? WHERE id = ?""", 
                       (username, id))
            cursor.execute("""UPDATE foods SET quality = ?
             WHERE id = ?""", 
                       (quality, id))
            
        elif quality == "mediocre":

            if recipient:
                response = ("You just ate {oc}%s which %s %s by %s about" +
                        " %s, %s, %s, and %s ago. Unfortunately, %s told you" +
                        " that the food was {mc}mediocre and it was."
                        ).format(oc=oc, mc=mc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
            else:
                problem = random.choice(("smelled funny",
                "was soggy inside", "had a disagreeable ingredient",
                "was a bit squished", "got stuck between your teeth",
                "gave you backpain", "needed extra salt and/or sugar"))
                response = ("You just ate {oc}%s which %s %s by %s about" +
                        " %s, %s, %s, and %s ago. Unfortunately, the food %s" +
                        " and was {mc}mediocre.").format(oc=oc, mc=mc) % \
                ((foodname, inflection1, verb, other) + 
                timeparts + (problem,))
            
            
            cursor.execute("""UPDATE foods SET eater = ? WHERE id = ?""", 
                       (username, id))
            cursor.execute("""UPDATE foods SET quality = ?
             WHERE id = ?""", 
                       (quality, id))
            
        elif quality == "poisoned":
            if recipient:
                if random.random()>0.5:
                    response = ("You almost ate {oc}%s which %s %s by %s" + 
                        " about %s, %s, %s, and %s ago. However, you" +
                        " noticed %s's dead body nearby and left the" + 
                        " {pc}poisoned food alone."
                        ).format(oc=oc, pc=pc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
                    #the person ate it anyways
                    username = recipient
                else:
                    response = ("You just ate {oc}%s which %s %s by %s" +
                        " about %s, %s, %s, and %s ago. Unfortunately, the" +
                        " food was {pc}poisoned and %s's life is now" +
                        " spared."
                        ).format(oc=oc, pc=pc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
            else:
                problem = random.choice(("was very deadly",
                    "was biologically contaminated", "was radioactive",
                    "smelled like almonds", "got you hooked on nicotine"))
                response = ("You just ate {oc}%s which %s %s by %s about" +
                        " %s, %s, %s, and %s ago. Unfortunately, the" +
                        " food %s" +
                        " and you were {pc}poisoned."
                        ).format(oc=oc, pc=pc) % \
                        ((foodname, inflection1, verb, other) + 
                         timeparts + (problem,))
            
            
            cursor.execute("""UPDATE foods SET eater = ? WHERE id = ?""", 
                       (username, id))
            cursor.execute("""UPDATE foods SET quality = ?
             WHERE id = ?""", 
                       (quality, id))

        elif quality == "trash":
            if recipient:
                if random.random()>0.5:
                    response = ("You were going to eat {oc}%s which %s" +
                        " %s by %s" +
                        " about %s, %s, %s, and %s ago. Unfortunately, the" +
                        " food was {tc}trash and so %s already threw it" +
                        " away for you."
                        ).format(oc=oc, tc=tc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
                else:
                    response = ("You just ate {oc}%s which %s %s by %s" +
                        " about %s, %s, %s, and %s ago. Unfortunately, %s" +
                        " threw up on it and so you knew it was {tc}trash."
                        ).format(oc=oc, tc=tc) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
            else:
                problem = random.choice(("fell onto the floor",
                    "had %s ants in it" % (random.choice(["army",
                                    "imported fire", "killer"])),
                    "was recalled by the government",
                    "got squished in the fridge",
                    "said something about your mom",
                    "got assimilated by Borg nanites and resisted futilely",
                    "was blasphemous to your religion",
                    "had fungus growing on it"))
                response = ("You were going to eat {oc}%s which" +
                            " %s %s by %s" +
                             " about" +
                             " %s, %s, %s, and %s ago. Unfortunately, the" +
                             " food %s and you threw it into the {tc}trash" +
                             ".").format(oc=oc, tc=tc) % \
                ((foodname, inflection1, verb, other) +
                  timeparts + (problem,))
            cursor.execute("""UPDATE foods SET eater = ? WHERE id = ?""", 
                       (username, id))
            cursor.execute("""UPDATE foods SET quality = ?
                    WHERE id = ?""", 
                    (quality, id))
        elif quality == "inaccessible":
            if recipient:
                if random.random()>0.5:
                    response = ("You were going to eat {oc}%s which %s" +
                        " %s by %s" +
                        " about %s, %s, %s, and %s ago. Unfortunately, %s" +
                        " dropped the food into the grating and it became" +
                        " forever {ic}inaccessible."
                        ).format(oc=oc, ic=ic) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
                else:
                    response = ("You were going to eat {oc}%s which %s" +
                        " %s by %s" +
                        " about %s, %s, %s, and %s ago. Unfortunately, %s" +
                        " already stored it inside a safe and forgot the" +
                        " combination, making it {ic}inaccessible."
                        ).format(oc=oc, ic=ic) % ((foodname, inflection1, 
                        verb, other) + timeparts + (recipient,))
            else:
                problem = random.choice((
                    "was encased in ice frozen by an inverse perpetual" +
                    " motion machine and was",
                    "had teleportisis and was",
                    "grew wings to fly away and became",
                    "was extremely light and your breath blew it away and" +
                    " made it become",
                    "had too much defensive firepower baked in and was",
                    "took out a restraining order against you and was",
                    "was stored under a falling bucket of indestructium" +
                    " cement and became",
                    "got sucked into a spontaneous and rapidly closing" +
                    " wormhole where it was",
                    ))
                response = ("You were going to eat {oc}%s which" +
                            " %s %s by %s" +
                             " about" +
                             " %s, %s, %s, and %s ago. Unfortunately, " +
                             "the food %s {ic}inaccessible."
                             ).format(oc=oc, ic=ic) % \
                ((foodname, inflection1, verb, other) +
                  timeparts + (problem,))
            cursor.execute("""UPDATE foods SET eater = ? WHERE id = ?""", 
                       (username, id))
            cursor.execute("""UPDATE foods SET quality = ?
                    WHERE id = ?""", 
                    (quality, id))
        else:
            response = "Some terrible has just happened."
        irc.reply(response)
        if ("cake" in foodname and
            "real" not in foodname and
            "true" not in foodname):
            if random.random()>0.5:
                irc.reply('You hear a synthesized voice tell you "Please' +
                        ' note that here at Aperture labs, we are diligently' +
                        ' working to resolve this issue and ensure' +
                        ' reliable product delivery".')
            else:
                irc.reply('You hear a synthesized voice tell you "At' +
                          ' Aperture Labs, we promise that the next cake' +
                          ' will be real or you won\'t have to eat it"')
        
        
    eat = wrap(eat, ['channel', additional('something')])

    def food(self, irc, msg, args, channel, other):
        """: shows how much food you, or if entered, other
        has eaten and baked and how much of it is poisonous. """
        db = self.getDb(channel)
        cursor = db.cursor()
        
        username = msg.nick.lower()
        if other:
            other = other.lower()
        
        if other:
            if (username != other and not
            ircdb.checkCapability(msg.prefix, 'owner') and not
            ircdb.checkCapability(msg.prefix, 'admin')):
                irc.reply("Using this command on another person is" +
                          " currently not supported for non-admins.")
                return
        if other:
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(baker) = ?
                AND verb = 'baked'""",
                [other])
            bakedqraw = cursor.fetchall()
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(baker) = ?
                AND verb = 'cooked'""",
                [other])
            cookedqraw = cursor.fetchall()
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(eater) = ?
                """,
                [other])
            eatenqraw = cursor.fetchall()
            
            qraw = (bakedqraw, cookedqraw, eatenqraw)
            qualities = [(len(i), i.count(("delicious",)),
                         i.count(("mediocre",)), i.count(("trash",)),
                         i.count(("poisoned",)), i.count(("inaccessible",)))
                         for i in qraw]
            irc.reply(("{other} has baked {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic, other=other) %
                      (qualities[0]))
            irc.reply(("{other} has cooked {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic, other=other) %
                      (qualities[1]))
            irc.reply(("{other} has eaten {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic, other=other) %
                      (qualities[2]))

        else:
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(baker) = ?
                AND verb = 'baked'""",
                [username])
            bakedqraw = cursor.fetchall()
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(baker) = ?
                AND verb = 'cooked'""",
                [username])
            cookedqraw = cursor.fetchall()
            cursor.execute(
                """SELECT quality FROM foods WHERE LOWER(eater) = ?
                """,
                [username])
            eatenqraw = cursor.fetchall()
            
            qraw = (bakedqraw, cookedqraw, eatenqraw)
            qualities = [(len(i), i.count(("delicious",)),
                         i.count(("mediocre",)), i.count(("trash",)),
                         i.count(("poisoned",)), i.count(("poisoned",)))
                         for i in qraw]
            irc.reply(("You have baked {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic) %
                      (qualities[0]))
            irc.reply(("You have baked {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic) %
                      (qualities[1]))
            irc.reply(("You have baked {oc}%s foods and {dc}%s of " +
            "them were " + 
            "delicious, {mc}%s were mediocre, {tc}%s were trash, " +
             "{pc}%s were poisoned, and {ic}%s were inaccessible."
             ).format(oc=oc, dc=dc, mc=mc, tc=tc, pc=pc, ic=ic) %
                      (qualities[2]))
        
        
    food = wrap(food, ['channel', additional('something')])

    


Class = BakeIt


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
