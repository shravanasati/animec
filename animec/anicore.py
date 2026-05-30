# -*- coding: utf-8 -*-

import re

from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import HTTPError
from animec.errors import NoResultFound
from animec.helpers import escape_url


def _collapse_whitespace(s: str):
    return " ".join([i.strip() for i in s.split() if i.strip()])


def clean_number(s: str):
    return int(s.replace(",", ""))


class Anime:
    """Retrieves anime info via `myanimelist <https://myanimelist.net/>`__.

    Parameters
    ----------
    query: `str <https://docs.python.org/3/library/string.html#module-string>`__
        The query to be searched for.

    Attributes
    ----------
    url
        Returns the url of the anime main page
    id
        Returns the MAL ID of the anime
    name
        Returns the main name of the anime

    title_english
        Returns the english title
    title_jp
        Returns the japanese title
    alt_titles
        Returns alternative titles


    score
        The score of the anime
    episodes
        The episode count of the anime
    avg_episode_duration
        The average episode duration of the anime
    aired
        Anime's airing time
    broadcast
        The broadcast day of the series
    rating
        Rating given to the anime
    ranked
        Anime's ranking
    popularity
        The popularity of the anime
    num_list_users
        Count of people who have this anime in their lists
    num_scoring_users
        Count of people who have rated this anime
    favorites
        Count of people who tagged the anime as their favourite

    type
        Series type
    status
        Series current status with reference to airing
    producers: `list <https://docs.python.org/3/tutorial/datastructures.html>`__
        List of studios which contributed to the production of the series
    genres: `list <https://docs.python.org/3/tutorial/datastructures.html>`__
        List of anime genres or kind
    themes: `list <https://docs.python.org/3/tutorial/datastructures.html>`__
        List of anime themes
    demographics: `list <https://docs.python.org/3/tutorial/datastructures.html>`__
        List of anime demographics
    related_entries: list[dict[str, str]]
        Related entries of the anime (sequel/prequel/adaptation)
        The dictionary contains these keys: relation, title and url.

    description
        Short description about the anime
    poster
        Anime thumbnail
    teaser
        Official anime teaser/promotion
    """

    def __init__(self) -> None:
        self.url: str | None = None
        self.id: int | None = None
        self.name: str | None = None

        self.title_english: str | None = None
        self.title_jp: str | None = None
        self.alt_titles: str | None = None

        self.episodes = None
        self.premiered = None
        self.aired = None
        self.broadcast = None
        self.rating = None
        self.ranked = None
        self.score = None
        self.popularity = None
        self.favorites = None

        self.type = None
        self.status = None
        self.producers = None

        self.description = None
        self.poster = None

    @classmethod
    def search(cls, query: str):
        query = escape_url(query)

        to_open = f"https://myanimelist.net/anime.php?q={query}"
        encoded_url = to_open.encode("ascii", "ignore")

        try:
            html_page = urlopen(encoded_url.decode("utf-8"))
        except HTTPError:
            raise NoResultFound("Can't find a matching result.")

        soup = BeautifulSoup(html_page, "html.parser")

        anime_div = soup.find("td", {"class": "borderClass bgColor0"})
        url = anime_div.find("a", href=True)["href"]

        # quote the non-ascii characters which may possibly exist in the anime name
        url = escape_url(url)

        anime_page_open = urlopen(url)
        obj = cls()
        obj.__process_anime_page(anime_page_open)
        url_parts = anime_page_open.geturl().split("/")
        if len(url_parts) > 2:
            obj.id = int(url_parts[-2])
        return obj

    @classmethod
    def from_id(cls, mal_id: int):
        obj = cls()
        to_open = f"https://myanimelist.net/anime/{mal_id}"
        try:
            anime_page_open = urlopen(to_open)
        except HTTPError:
            raise NoResultFound(f"Can't find a matching result for MAL ID: '{mal_id}'")
        obj.__process_anime_page(anime_page_open)
        obj.id = mal_id
        return obj

    def __process_anime_page(self, anime_page_resp):
        anime_soup = BeautifulSoup(anime_page_resp, "html.parser")
        self._related_entry_tiles = anime_soup.select(".entries-tile .content")

        name = anime_soup.find("h1", {"class": "title-name h1_bold_none"})

        self.__spaceit_divs = anime_soup.find_all("div", {"class": "spaceit_pad"})
        dark_text = anime_soup.find_all("span", {"class": "dark_text"})
        self._dark = dark_text

        title_english = self._divCh_("English:")
        title_jp = self._divCh_("Japanese:")
        alt_titles = self._divCh_("Synonyms:")

        episodes = self._divCh_("Episodes:")
        avg_episode_duration = self._divCh_("Duration:")
        premiered = self._divCh_("Premiered:")
        aired = self._divCh_("Aired:")
        broadcast = self._divCh_("Broadcast:")

        rating = self._parent_(element=dark_text, txt="Rating:")
        score = anime_soup.select_one(".score-label")
        popularity = self._parent_(element=dark_text, txt="Popularity:")
        favorites = self._parent_(element=dark_text, txt="Favorites:")
        num_list_users = self._parent_(element=dark_text, txt="Members:")
        num_scoring_users = anime_soup.find("span", {"itemprop": "ratingCount"}).text
        _type = self._parent_(element=dark_text, txt="Type:")
        status = self._parent_(element=dark_text, txt="Status:")
        producers = self._parent_(element=dark_text, txt="Producers:").split(", ")

        ranked_text = str(
            anime_soup.find(
                "div",
                {
                    "class": "spaceit_pad po-r js-statistics-info di-ib",
                    "data-id": "info2",
                },
            )
        )
        ranked = re.search("#.*<", ranked_text)
        ranked = ranked.group().split("<")[0] if ranked else None

        description = anime_soup.find("p", {"itemprop": "description"}).text
        poster = anime_soup.find("img", {"itemprop": "image"})["data-src"]

        self.url = anime_page_resp.geturl() or None
        self.name = name.text or None

        self.title_english = title_english or None
        self.title_jp = title_jp or None
        self.alt_titles = alt_titles or None

        self.episodes = episodes or None
        self.premiered = premiered or None
        self.aired = aired or None
        self.broadcast = broadcast or None
        self.rating = rating or None
        self.avg_episode_duration = avg_episode_duration or None
        self.ranked = ranked or None
        self.popularity = popularity or None
        self.favorites = favorites or None
        self.num_list_users = clean_number(num_list_users) or None
        self.num_scoring_users = clean_number(num_scoring_users) or None
        self.score = float(score.text) or None

        self.type = _type or None
        self.status = status or None
        self.producers = producers

        self.description = description or None
        self.poster = poster or None

    def is_nsfw(self) -> bool:
        """
        Returns
        -------
        bool
            Returns if the series is nsfw
        """

        return any(i in self.rating.lower() for i in ["nudity", "hentai"])

    @property
    def genres(self):
        genres = []

        for container in self._dark:
            if "Genres" in container.text or "Genre" in container.text:
                parent = container.parent
                links = parent.find_all("a")

                for sub in links:
                    genres.append(sub.text)

        return genres

    @property
    def themes(self):
        themes_ = []
        for container in self._dark:
            if "Themes" in container.text or "Theme" in container.text:
                parent = container.parent
                links = parent.find_all("a")

                for sub in links:
                    themes_.append(sub.text)

        return themes_

    @property
    def demographics(self):
        demographics_ = []
        for container in self._dark:
            if "Demographics" in container.text or "Demographic" in container.text:
                parent = container.parent
                links = parent.find_all("a")

                for sub in links:
                    demographics_.append(sub.text)

        return demographics_

    @property
    def related_entries(self):
        entries = []
        for tile in self._related_entry_tiles:
            entries.append(
                {
                    "relation": _collapse_whitespace(tile.select_one(".relation").text),
                    "title": _collapse_whitespace(tile.select_one(".title > a").text),
                    "url": tile.select_one(".title > a").attrs["href"],
                }
            )

        return entries

    @property
    def teaser(self):
        url = urlopen(self.url + "/video", timeout=5)
        soup = BeautifulSoup(url, "html.parser")

        div = soup.find("div", {"class": "video-list-outer po-r pv"})
        teaser_link = div.find_all(
            "a", {"class": "iframe js-fancybox-video video-list di-ib po-r"}
        )[0]["href"]

        if teaser_link and "youtube" in teaser_link:
            _id = teaser_link.split("embed/")[1].split("?")[0]
            teaser_link = f"https://www.youtube.com/watch?v={_id}"

        return teaser_link or None

    def _divCh_(self, txt: str):
        for container in self.__spaceit_divs:
            if txt in container.text:
                div_text = container.text.split(txt)[1].split()
                return " ".join(div_text)

    def _parent_(self, element: list, txt: str):
        for e in element:
            if txt in e.text:
                returned_text = e.parent.text.split(txt)[1].split()
                return " ".join(returned_text)

    def recommend(self) -> list:
        """
        Returns
        -------
        list
            Returns suitable recommendations based on the anime referred while declaring the class
        """

        anime_page = urlopen(self.url + "/userrecs")
        soup = BeautifulSoup(anime_page, "html.parser")

        headers = soup.find_all("strong", limit=15)

        recommendations = [i.get_text() for i in headers]

        ri = [i for i in recommendations if not i.isdigit()]
        ri.pop(0)

        return ri[:5]


if __name__ == "__main__":
    a = Anime.search("frieren")
    print(a.num_list_users, a.num_scoring_users)
    a2 = Anime.from_id(1)
    print(a2.num_list_users, a2.num_scoring_users)

    # import time
    # from concurrent.futures import ThreadPoolExecutor
    # now = time.time()
    # with ThreadPoolExecutor(10) as pool:
    #     pool.map(Anime.from_id, range(1, 610))

    # finish = time.time()
    # print(finish - now)
