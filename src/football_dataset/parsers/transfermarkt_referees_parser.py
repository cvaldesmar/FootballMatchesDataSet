from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from .errors import ParserError


class TransfermarktRefereesParser:
    def parse_referee_links(self, html: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find("th", string="Árbitros")
        if heading is None:
            raise ParserError("Transfermarkt no contiene la tabla de árbitros")
        table = heading.find_parent("table", class_="items")
        if table is None:
            raise ParserError("No se encontró la tabla de árbitros de Transfermarkt")
        result: list[tuple[str, str]] = []
        for element in table.select(".hauptlink:not(.zentriert)"):
            anchor = element.find("a")
            href = anchor.get("href") if anchor is not None else None
            if anchor is not None and anchor.get_text(strip=True) and isinstance(href, str):
                result.append((anchor.get_text(strip=True), href))
        if not result:
            raise ParserError("La tabla de árbitros no contiene enlaces")
        return result

    def parse_matches(
        self, html: str, referee_name: str, referee_id: int
    ) -> list[dict[str, object]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("div", class_="content-box-headline--logo")
        if table is None or table.find_next_sibling() is None:
            raise ParserError("Transfermarkt no contiene la tabla de partidos del árbitro")
        result: list[dict[str, object]] = []
        sibling = table.find_next_sibling()
        if sibling is None:
            raise ParserError("Transfermarkt no contiene la tabla de partidos del árbitro")
        for tr in sibling.find_all("tr")[2:]:
            tds = tr.find_all("td")
            teams = tr.find_all("td", class_="no-border-links")
            if len(tds) < 7 or len(teams) < 2:
                continue
            try:
                date_value = datetime.strptime(tds[1].get_text(strip=True), "%d/%m/%Y").strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                continue
            links = [team.find("a") for team in teams[:2]]
            if len(links) < 2 or links[0] is None or links[1] is None:
                continue
            result.append(
                {
                    "date": date_value,
                    "home_name": links[0].get_text(strip=True),
                    "away_name": links[1].get_text(strip=True),
                    "referee_name": referee_name,
                    "referee_id": referee_id,
                }
            )
        return result
