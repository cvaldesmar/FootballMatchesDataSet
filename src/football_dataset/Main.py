"""
Football Matches DataSet Generator & Scraper
Autor original: Ricardo Moya (https://github.com/RicardoMoya/FootballMatchesDataSet)
Refactorizado y modernizado para ejecución flexible y modular vía CLI.
"""

import argparse
import csv
import logging
import os
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any, cast

from colorama import Fore, Style, init
from icecream import install  # type: ignore[attr-defined]

from . import Const as const
from .context import ExecutionContext
from .dataset_io import append_season, write_csv_header
from .DatosTemporada import DatosTemporada
from .MarketHelper import MarketHelper
from .ml_features import build_ml_features
from .RefereesHelper import RefereesHelper
from .validation import DatasetValidator

logger = logging.getLogger(__name__)

# Inicializar logging, codificación segura y librerías de consola
if hasattr(sys.stdout, "reconfigure"):
    try:
        cast(Any, sys.stdout).reconfigure(encoding="utf-8")
        cast(Any, sys.stderr).reconfigure(encoding="utf-8")
    except Exception:
        pass

init(autoreset=True)
install()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def parse_arguments() -> Namespace:
    parser = argparse.ArgumentParser(
        description="Generador y Scraper del Dataset de Partidos de Fútbol (La Liga 1ª y 2ª División)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python Main.py --all
  python Main.py --from 2000
  python Main.py --from 1970 --to 2023
  python Main.py --to 2010
  python Main.py --latest
  python Main.py --seasons 2021-22 2022-23 --divisions 1 2 --output dataset.csv
  python Main.py --from-file --input-file TestSave.csv --output nuevo.csv
  python Main.py --list-seasons
        """,
    )

    # Temporadas y divisiones
    parser.add_argument(
        "-s",
        "--seasons",
        nargs="+",
        metavar="TEMPORADA",
        help="Lista de temporadas a procesar (ej: --seasons 2021-22 2022-23)",
    )
    parser.add_argument(
        "-d",
        "--divisions",
        nargs="+",
        type=int,
        choices=[1, 2],
        default=[1],
        help="Divisiones a procesar: 1 (Primera), 2 (Segunda), o ambas: 1 2 (por defecto: 1)",
    )
    parser.add_argument(
        "--all",
        "--all-seasons",
        dest="all_seasons",
        action="store_true",
        help="Procesar todas las temporadas históricas (1970-71 hasta la última disponible)",
    )
    parser.add_argument(
        "--from",
        "--from-year",
        "--since",
        dest="from_year",
        metavar="AÑO",
        help="Año de inicio. Ej: --from 1970 inicia en 1970-71. Si se omite junto con --to, inicia en 1970-71",
    )
    parser.add_argument(
        "--to",
        "--to-year",
        "--until",
        dest="to_year",
        metavar="AÑO",
        help="Año de fin. Ej: --to 2023 finaliza en 2022-23. Si se omite junto con --from, finaliza en la última disponible",
    )
    parser.add_argument(
        "--latest", action="store_true", help="Procesar únicamente la última temporada configurada"
    )

    # Origen de datos
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--source",
        choices=["web", "file"],
        default="web",
        help="Origen de los partidos: 'web' (scraping BDFutbol) o 'file' (cargar de CSV existente). Por defecto: web",
    )
    source_group.add_argument(
        "--from-file",
        dest="source",
        action="store_const",
        const="file",
        help="Atajo equivalente a --source file",
    )
    source_group.add_argument(
        "--from-web",
        dest="source",
        action="store_const",
        const="web",
        help="Atajo equivalente a --source web",
    )

    # Opciones de enriquecimiento de datos (Transfermarkt)
    parser.add_argument(
        "--skip-market",
        action="store_true",
        help="Omitir la obtención de valores de mercado de Transfermarkt (acelera la ejecución)",
    )
    parser.add_argument(
        "--skip-referees",
        action="store_true",
        help="Omitir la obtención de árbitros de Transfermarkt",
    )

    # Rutas de entrada/salida y utilidades
    parser.add_argument(
        "-i",
        "--input-file",
        default="TestSave.csv",
        help="Ruta del archivo CSV de entrada cuando se usa --source file (por defecto: TestSave.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="TestSave.csv",
        help="Ruta del archivo CSV de salida (por defecto: TestSave.csv)",
    )
    parser.add_argument(
        "--market-cache",
        default="market_values.json",
        help="Ruta del archivo JSON versionado de valores de mercado",
    )
    parser.add_argument(
        "--referees-cache",
        default="referees.json",
        help="Ruta del archivo JSON versionado de árbitros",
    )
    parser.add_argument(
        "--list-seasons", action="store_true", help="Muestra las temporadas disponibles y sale"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda la salida existente y omite divisiones/temporadas ya completas",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Guarda también la salida operativa en este fichero de log",
    )
    parser.add_argument(
        "--build-ml",
        action="store_true",
        help="Genera un dataset ML derivado al terminar la generación principal",
    )
    parser.add_argument(
        "--ml-output",
        default=None,
        help="Ruta del dataset ML derivado (por defecto: <output>_ml.csv)",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=0,
        metavar="N",
        help="Número máximo de errores de calidad tolerados por temporada (por defecto: 0)",
    )

    return parser.parse_args()


def print_banner(
   seasons: list[str],
   divisions: list[int],
   source: str,
   enable_market: bool,
   enable_referees: bool,
   output: str,
   input_file: str | None = None,
) -> None:
    print(Fore.CYAN + "=" * 65)
    print(Fore.GREEN + Style.BRIGHT + "   [*] FOOTBALL MATCHES DATASET GENERATOR [*]")
    print(Fore.CYAN + "=" * 65)
    print(
        f" {Fore.YELLOW}* Origen datos:{Style.RESET_ALL}       {'[WEB] BDFutbol' if source == 'web' else f'[FILE] Archivo local ({input_file})'}"
    )
    print(
        f" {Fore.YELLOW}* Divisiones:{Style.RESET_ALL}         {', '.join(f'{d}a' for d in divisions)}"
    )
    print(
        f" {Fore.YELLOW}* Temporadas ({len(seasons)}):{Style.RESET_ALL}    {', '.join(seasons[:5])}{'...' if len(seasons) > 5 else ''}"
    )
    print(
        f" {Fore.YELLOW}* Valores mercado:{Style.RESET_ALL}    {'[SI] Transfermarkt' if enable_market else '[NO] Desactivado'}"
    )
    print(
        f" {Fore.YELLOW}* Arbitros:{Style.RESET_ALL}           {'[SI] Transfermarkt' if enable_referees else '[NO] Desactivado'}"
    )
    print(f" {Fore.YELLOW}* Archivo destino:{Style.RESET_ALL}    {output}")
    print(Fore.CYAN + "=" * 65 + "\n")


def _configure_file_logging(path: str | None) -> None:
    if not path:
        return
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logging.getLogger().addHandler(handler)


def _completed_pairs(path: str) -> set[tuple[int, str]]:
    destination = Path(path)
    if not destination.exists() or destination.stat().st_size == 0:
        return set()
    completed: set[tuple[int, str]] = set()
    with destination.open(encoding="utf-8", newline="") as file:
        first_line = file.readline()
        if not first_line.startswith("# football_dataset_schema="):
            raise ValueError(f"El CSV existente no tiene metadato de esquema: {destination}")
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            try:
                completed.add((int(row["division"]), row["temporada"]))
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Fila inválida en el CSV existente: {row}") from error
    return completed


def main() -> None:
    args = parse_arguments()
    _configure_file_logging(args.log_file)

    if args.list_seasons:
        print(
            f"{Fore.GREEN}Temporadas cortas predeterminadas:{Style.RESET_ALL} {const.SHORT_TEMPORADAS}"
        )
        print(f"{Fore.GREEN}Última temporada:{Style.RESET_ALL} {const.LAST_TEMPORADA}")
        print(
            f"{Fore.GREEN}Temporadas desde el 2000 ({len(const.SINCE_2000_TEMPORADAS)}):{Style.RESET_ALL} {const.SINCE_2000_TEMPORADAS}"
        )
        print(
            f"{Fore.GREEN}Todas las temporadas ({len(const.ALL_TEMPORADAS)}):{Style.RESET_ALL} {const.ALL_TEMPORADAS}"
        )
        sys.exit(0)

    # Determinar qué temporadas procesar
    if args.all_seasons:
        temporadas = const.ALL_TEMPORADAS
    elif args.from_year is not None or args.to_year is not None:
        from_limit = 1970
        if args.from_year is not None:
            val_str = str(args.from_year).strip()
            from_limit = int(val_str.split("-")[0])

        to_limit = None
        if args.to_year is not None:
            val_str = str(args.to_year).strip()
            if "-" in val_str:
                to_limit = int(val_str.split("-")[0]) + 1
            else:
                to_limit = int(val_str)

        temporadas = []
        for season in const.ALL_TEMPORADAS:
            s_year = int(season.split("-")[0])
            e_year = s_year + 1
            if s_year < from_limit:
                continue
            if to_limit is not None and e_year > to_limit:
                continue
            temporadas.append(season)

        if not temporadas:
            print(
                f"{Fore.RED}Error: Ninguna temporada coincide con el rango --from {from_limit} --to {to_limit}{Style.RESET_ALL}"
            )
            sys.exit(1)
    elif args.latest:
        temporadas = const.LAST_TEMPORADA
    elif args.seasons:
        temporadas = args.seasons
    else:
        temporadas = const.SHORT_TEMPORADAS

    divisiones = args.divisions
    enable_market = not args.skip_market
    enable_referees = not args.skip_referees
    context = ExecutionContext(
        source=args.source,
        enable_market=enable_market,
        enable_referees=enable_referees,
        output_path=args.output,
        input_path=args.input_file,
        market_path=args.market_cache,
        referees_path=args.referees_cache,
    )
    market_helper = MarketHelper(context)
    referees_helper = RefereesHelper(context)
    validator = DatasetValidator()

    print_banner(
        seasons=temporadas,
        divisions=divisiones,
        source=args.source,
        enable_market=enable_market,
        enable_referees=enable_referees,
        output=args.output,
        input_file=args.input_file,
    )

    start_time = time.time()
    total_steps = len(divisiones) * len(temporadas)
    current_step = 0
    completed_pairs = _completed_pairs(args.output) if args.resume else set()
    if args.resume and completed_pairs:
        logger.info(
            "Reanudación activada: se omitirán %d pares división/temporada", len(completed_pairs)
        )
    if not args.resume:
        write_csv_header(args.output)
    elif not Path(args.output).exists():
        write_csv_header(args.output)
    incremental_matches = 0

    try:
        for division in divisiones:
            print(f"{Fore.BLUE}{Style.BRIGHT}==========================================")
            print(f"  PROCESANDO DIVISIÓN {division}ª")
            print(f"=========================================={Style.RESET_ALL}")

            for temporada in temporadas:
                current_step += 1
                if (division, temporada) in completed_pairs:
                    logger.info(
                        "Omitiendo división %s, temporada %s: ya presente", division, temporada
                    )
                    print(f"  OMITIDA {division}ª/{temporada}: ya presente en la salida")
                    continue
                logger.info("Iniciando división %s, temporada %s", division, temporada)
                print(
                    f"\n{Fore.CYAN}[{current_step}/{total_steps}] Procesando {division}ª División - Temporada {temporada}...{Style.RESET_ALL}"
                )

                season_data = DatosTemporada(
                    division,
                    temporada,
                    context=context,
                    market_helper=market_helper,
                    referees_helper=referees_helper,
                )
                report = validator.validate_matches(
                    [
                        match
                        for jornada in season_data.jornadas.values()
                        for match in jornada.values()
                    ],
                    expected_teams=len(season_data.clasificacion),
                    expected_matches=len(season_data.seasonLoader.matchesArray),
                    known_team_ids=season_data.clasificacion,
                    max_errors=args.max_errors,
                )
                for issue in report.issues:
                    log = logger.error if issue.severity == "error" else logger.warning
                    log("[%s] %s: %s", issue.code, issue.message, issue.context)
                if report.exceeds_error_threshold:
                    raise ValueError(
                        f"Dataset inválido en {division}ª/{temporada}: "
                        f"{len(report.errors)} errores (máximo permitido: {args.max_errors})"
                    )
                season_data.printSeasonWinner()
                context.add_season(division, temporada, season_data)
                written = append_season(args.output, season_data)
                incremental_matches += written
                completed_pairs.add((division, temporada))
                logger.info(
                    "Completada división %s, temporada %s: %d partidos",
                    division,
                    temporada,
                    written,
                )

        # Validación y guardado final de cachés. El dataset ya se ha escrito por temporada.
        print(f"\n{Fore.YELLOW}Guardando datos finales...{Style.RESET_ALL}")
        if enable_referees:
            referees_helper.save_values(args.referees_cache)
        if enable_market:
            market_helper.save_values(args.market_cache)
        num_partidos = incremental_matches

        elapsed = time.time() - start_time
        num_equipos = len(context.ids_to_team)

        print(f"\n{Fore.GREEN}{Style.BRIGHT}[OK] PROCESO COMPLETADO CON EXITO!{Style.RESET_ALL}")
        print(f"* Total partidos procesados: {Fore.YELLOW}{num_partidos}{Style.RESET_ALL}")
        print(f"* Total equipos identificados: {Fore.YELLOW}{num_equipos}{Style.RESET_ALL}")
        print(f"* Dataset generado en: {Fore.GREEN}{os.path.abspath(args.output)}{Style.RESET_ALL}")
        print(f"* Tiempo empleado: {elapsed:.2f} segundos\n")
        if args.build_ml:
            ml_output = args.ml_output or str(
                Path(args.output).with_name(f"{Path(args.output).stem}_ml.csv")
            )
            ml_count = build_ml_features(args.output, ml_output)
            print(f"* Dataset ML generado en: {os.path.abspath(ml_output)} ({ml_count} filas)\n")

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Proceso interrumpido por el usuario.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error durante la ejecución: {e}{Style.RESET_ALL}")
        raise


if __name__ == "__main__":
    main()
