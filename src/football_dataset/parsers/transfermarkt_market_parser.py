from __future__ import annotations

from datetime import date, datetime

from bs4 import BeautifulSoup

from .errors import ParserError


class TransfermarktMarketParser:
    def parse_dates(self, html: str) -> dict[date, dict[str, float]]:
        soup = BeautifulSoup(html, "html.parser")
        select = soup.find("select", class_="chzn-select")
        if select is None:
            raise ParserError("Transfermarkt no contiene el selector de fechas de mercado")
        dates: dict[date, dict[str, float]] = {}
        for option in select.find_all("option"):
            raw_value = option.get("value")
            value = raw_value if isinstance(raw_value, str) else ""
            try:
                dates[datetime.strptime(value, "%Y-%m-%d").date()] = {}
            except (TypeError, ValueError) as error:
                raise ParserError(f"Fecha de mercado inválida: {value}") from error
        if not dates:
            raise ParserError("El selector de Transfermarkt no contiene fechas")
        return dates

    def parse_team_values(self, html: str) -> dict[str, float]:
        soup = BeautifulSoup(html, "html.parser")
        nodes = soup.find_all("td", class_="hauptlink no-border-links")
        if not nodes:
            raise ParserError("Transfermarkt no contiene valores de equipos")
        values: dict[str, float] = {}
        for node in nodes:
            anchor = node.find("a")
            sibling = node.find_next_siblings()
            if anchor is None or len(sibling) < 2 or sibling[1].find("a") is None:
                continue
            value_anchor = sibling[1].find("a")
            if value_anchor is None:
                continue
            raw = value_anchor.get_text(strip=True)
            try:
                title = anchor.get("title")
                team_name = title if isinstance(title, str) else anchor.get_text(strip=True)
                values[team_name] = (
                    -1.0
                    if raw == "-"
                    else float(raw.split()[0].replace(",", "."))
                    * (1000 if "mil mill." in raw else 1)
                )
            except (TypeError, ValueError) as error:
                raise ParserError(
                    f"Valor de mercado inválido para {anchor.get_text(strip=True)}: {raw}"
                ) from error
        if not values:
            raise ParserError("No se pudieron extraer valores de equipos de Transfermarkt")
        return values
