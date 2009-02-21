# Uses the IMDbPY package in http mode against imdb.com
# This isn't strictly legal: http://www.imdb.com/help/show_leaf?usedatasoftware
#
# Note that it will return porn movies by default.

from .. imdb import IMDb, IMDbDataAccessError, IMDbError

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption

import logging

help = {'imdb': 'Looks up movies on IMDB.com.'}

class IMDB(Processor):
    "imdb [search] [character|company|episode|movie|person] <terms> [result <index>]"
    feature = 'imdb'

    def setup(self):
        self.imdb = IMDb(accessSystem='http', adultSearch=1)
        self.log = logging.getLogger("module.imdb")
        self.name_keys = {
                "character": "long imdb name",
                "company": "long imdb name",
                "episode": "long imdb title",
                "movie": "long imdb title",
                "person": "name",
        }

    @match(r'^imdb(?:\s+search)?(?:\s+(character|company|episode|movie|person))?\s+(.+?)(?:\s+result\s+(\d+))?$')
    def search(self, event, search_type, terms, index):
        if search_type is None:
            search_type = "movie"
        if index is not None:
            index = int(index) - 1

        result = None
        try:
            if terms.isdigit():
                result = getattr(self.imdb, "get_" + search_type)(terms)
            else:
                results = getattr(self.imdb, "search_" + search_type)(terms)

                if len(results) == 1:
                    index = 0

                if index is not None:
                    result = results[index]
                    self.imdb.update(result)

        except IMDbDataAccessError, e:
            event.addresponse(u"Error: %s" % e[0]["errmsg"])

        except IMDbError, e:
            event.addresponse(u"Something must be wrong with IMDB today")
            raise

        if result is not None:
            try:
                event.addresponse(u"Found " + getattr(self, "display_" + search_type)(result))
            except Exception, e:
                event.addresponse(u"Whoops, the IMDB module has a bug. Admin! Help!")
                raise
            return

        if len(results) == 0:
            event.addresponse(u"Sorry, couldn't find anything by that name")
        else:
            results = [x[self.name_keys[search_type]] for x in results]
            results = enumerate(results)
            results = [u"%i: %s" % (x[0] + 1, x[1]) for x in results]
            more = (u"", u">")[len(results) == 20]
            event.addresponse(u"Found %s%i matches: %s" % (more, len(results), u", ".join(results)))

    def display_character(self, character):
        desc = u"%s: %s." % (character.characterID, character["long imdb name"])
        filmography = character.get("filmography", ())
        if len(filmography):
            more = (u"", u" etc")[len(filmography) > 5]
            desc += u" Appeared in %s%s." % (", ".join(x["long imdb title"] for x in filmography[:5]), more)
        if character.has_key("introduction"):
            desc += u" Bio: %s" % character["introduction"]
        return desc

    def display_company(self, company):
        desc = "%s: %s" % (company.companyID, company["long imdb name"])
        for key, title in (
                (u"production companies", u"Produced"),
                (u"distributors", u"Distributed"),
                (u"miscellaneous companies", u"Was involved in")):
            if len(company.get(key, ())) > 0:
                more = (u"", u" etc.")[len(company[key]) > 3]
                desc += u" %s %s%s" % (title, ", ".join(x["long imdb title"] for x in company[key][:3]), more)
        return desc

    def display_episode(self, episode):
        desc = u"%s: %s s%02ie%02i %s(%s)." % (
                episode.movieID, episode["series title"], episode["season"],
                episode["episode"], episode["title"], episode["year"])
        if len(episode.get("director", ())) > 0:
            desc += u" Dir: %s." % (u", ".join(x["name"] for x in episode["director"]))
        if len(episode.get("cast", ())) > 0:
            desc += u" Starring: %s." % (u", ".join(x["name"] for x in episode["cast"][:3]))
        if episode.has_key("rating"):
            desc += u" Rated: %.1f " % episode["rating"]
        desc += u", ".join(movie.get("genres", ()))
        desc += u" Plot: %s" % episode.get("plot outline", u"Unknown")
        return desc

    def display_movie(self, movie):
        desc = u"%s: %s." % (movie.movieID, movie["long imdb title"])
        if len(movie.get("director", ())) > 0:
            desc += u" Dir: %s." % (u", ".join(x["name"] for x in movie["director"]))
        if len(movie.get("cast", ())) > 0:
            desc += u" Starring: %s." % (u", ".join(x["name"] for x in movie["cast"][:3]))
        if movie.has_key("rating"):
            desc += u" Rated: %.1f " % movie["rating"]
        desc += u", ".join(movie.get("genres", ()))
        desc += u" Plot: %s" % movie.get("plot outline", u"Unknown")
        return desc

    def display_person(self, person):
        # Bleh: normally in bio
        #desc = u"%s: %s, Born " % (person.personID, person["name"])
        #if person["birth name"] != person["name"]:
        #    desc += u"%s " % person["birth name"]
        #desc += u"%s. %s" % (person["birth date"], u" ".join(person["mini biography"]))
        return u"%s: %s. %s. Bio: %s" % (person.personID, person["name"],
                u", ".join(role.title() for role in (
                    u"actor", u"animation department", u"art department",
                    u"art director", u"assistant director", u"camera department",
                    u"casting department", u"casting director", u"cinematographer",
                    u"composer", u"costume department", u"costume designer",
                    u"director", u"editorial department", u"editor",
                    u"make up department", u"music department", u"producer",
                    u"production designer", u"set decorator", u"sound department",
                    u"speccial effects department", u"stunts", u"transport department",
                    u"visual effects department", u"writer", u"miscellaneous crew"
                ) if person.has_key(role)), u" ".join(person["mini biography"]))

# vi: set et sta sw=4 ts=4:
