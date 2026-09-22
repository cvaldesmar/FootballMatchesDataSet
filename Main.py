# -*- coding: utf-8 -*-
"""
Football Matches DataSet Generator & Scraper
Autor original: Ricardo Moya (https://github.com/RicardoMoya/FootballMatchesDataSet)
Refactorizado y modernizado para ejecución flexible y modular vía CLI.
"""

import sys
import os
import time
import argparse
from colorama import init, Fore, Style
from icecream import install

import Const as const
import UtilsAndGlobals as ut
from DatosTemporada import DatosTemporada

# Inicializar codificación segura y librerías de consola
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

init(autoreset=True)
install()


def parse_arguments():
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
        """
    )

    # Temporadas y divisiones
    parser.add_argument(
        "-s", "--seasons",
        nargs="+",
        metavar="TEMPORADA",
        help="Lista de temporadas a procesar (ej: --seasons 2021-22 2022-23)"
    )
    parser.add_argument(
        "-d", "--divisions",
        nargs="+",
        type=int,
        choices=[1, 2],
        default=[1],
        help="Divisiones a procesar: 1 (Primera), 2 (Segunda), o ambas: 1 2 (por defecto: 1)"
    )
    parser.add_argument(
        "--all", "--all-seasons",
        dest="all_seasons",
        action="store_true",
        help="Procesar todas las temporadas históricas (1970-71 hasta la última disponible)"
    )
    parser.add_argument(
        "--from", "--from-year", "--since",
        dest="from_year",
        metavar="AÑO",
        help="Año de inicio. Ej: --from 1970 inicia en 1970-71. Si se omite junto con --to, inicia en 1970-71"
    )
    parser.add_argument(
        "--to", "--to-year", "--until",
        dest="to_year",
        metavar="AÑO",
        help="Año de fin. Ej: --to 2023 finaliza en 2022-23. Si se omite junto con --from, finaliza en la última disponible"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Procesar únicamente la última temporada configurada"
    )

    # Origen de datos
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--source",
        choices=["web", "file"],
        default="web",
        help="Origen de los partidos: 'web' (scraping BDFutbol) o 'file' (cargar de CSV existente). Por defecto: web"
    )
    source_group.add_argument(
        "--from-file",
        dest="source",
        action="store_const",
        const="file",
        help="Atajo equivalente a --source file"
    )
    source_group.add_argument(
        "--from-web",
        dest="source",
        action="store_const",
        const="web",
        help="Atajo equivalente a --source web"
    )

    # Opciones de enriquecimiento de datos (Transfermarkt)
    parser.add_argument(
        "--skip-market",
        action="store_true",
        help="Omitir la obtención de valores de mercado de Transfermarkt (acelera la ejecución)"
    )
    parser.add_argument(
        "--skip-referees",
        action="store_true",
        help="Omitir la obtención de árbitros de Transfermarkt"
    )

    # Rutas de entrada/salida y utilidades
    parser.add_argument(
        "-i", "--input-file",
        default="TestSave.csv",
        help="Ruta del archivo CSV de entrada cuando se usa --source file (por defecto: TestSave.csv)"
    )
    parser.add_argument(
        "-o", "--output",
        default="TestSave.csv",
        help="Ruta del archivo CSV de salida (por defecto: TestSave.csv)"
    )
    parser.add_argument(
        "--market-cache",
        default="market_values.pickle",
        help="Ruta del archivo caché de valores de mercado (.pickle)"
    )
    parser.add_argument(
        "--referees-cache",
        default="Referees.pickle",
        help="Ruta del archivo caché de árbitros (.pickle)"
    )
    parser.add_argument(
        "--list-seasons",
        action="store_true",
        help="Muestra las temporadas disponibles y sale"
    )

    return parser.parse_args()


def print_banner(seasons, divisions, source, enable_market, enable_referees, output, input_file=None):
    print(Fore.CYAN + "=" * 65)
    print(Fore.GREEN + Style.BRIGHT + "   [*] FOOTBALL MATCHES DATASET GENERATOR [*]")
    print(Fore.CYAN + "=" * 65)
    print(f" {Fore.YELLOW}* Origen datos:{Style.RESET_ALL}       {'[WEB] BDFutbol' if source == 'web' else f'[FILE] Archivo local ({input_file})'}")
    print(f" {Fore.YELLOW}* Divisiones:{Style.RESET_ALL}         {', '.join(f'{d}a' for d in divisions)}")
    print(f" {Fore.YELLOW}* Temporadas ({len(seasons)}):{Style.RESET_ALL}    {', '.join(seasons[:5])}{'...' if len(seasons) > 5 else ''}")
    print(f" {Fore.YELLOW}* Valores mercado:{Style.RESET_ALL}    {'[SI] Transfermarkt' if enable_market else '[NO] Desactivado'}")
    print(f" {Fore.YELLOW}* Arbitros:{Style.RESET_ALL}           {'[SI] Transfermarkt' if enable_referees else '[NO] Desactivado'}")
    print(f" {Fore.YELLOW}* Archivo destino:{Style.RESET_ALL}    {output}")
    print(Fore.CYAN + "=" * 65 + "\n")


def main():
    args = parse_arguments()

    if args.list_seasons:
        print(f"{Fore.GREEN}Temporadas cortas predeterminadas:{Style.RESET_ALL} {const.SHORT_TEMPORADAS}")
        print(f"{Fore.GREEN}Última temporada:{Style.RESET_ALL} {const.LAST_TEMPORADA}")
        print(f"{Fore.GREEN}Temporadas desde el 2000 ({len(const.SINCE_2000_TEMPORADAS)}):{Style.RESET_ALL} {const.SINCE_2000_TEMPORADAS}")
        print(f"{Fore.GREEN}Todas las temporadas ({len(const.ALL_TEMPORADAS)}):{Style.RESET_ALL} {const.ALL_TEMPORADAS}")
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
            print(f"{Fore.RED}Error: Ninguna temporada coincide con el rango --from {from_limit} --to {to_limit}{Style.RESET_ALL}")
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

    # Configurar el contexto global de ejecución
    ut.configure(
        source=args.source,
        enable_market=enable_market,
        enable_referees=enable_referees,
        output_path=args.output,
        input_path=args.input_file,
        market_path=args.market_cache,
        referees_path=args.referees_cache
    )

    print_banner(
        seasons=temporadas,
        divisions=divisiones,
        source=args.source,
        enable_market=enable_market,
        enable_referees=enable_referees,
        output=args.output,
        input_file=args.input_file
    )

    start_time = time.time()
    total_steps = len(divisiones) * len(temporadas)
    current_step = 0

    try:
        for division in divisiones:
            print(f"{Fore.BLUE}{Style.BRIGHT}==========================================")
            print(f"  PROCESANDO DIVISIÓN {division}ª")
            print(f"=========================================={Style.RESET_ALL}")

            for temporada in temporadas:
                current_step += 1
                print(f"\n{Fore.CYAN}[{current_step}/{total_steps}] Procesando {division}ª División - Temporada {temporada}...{Style.RESET_ALL}")

                season_data = DatosTemporada(division, temporada)
                season_data.printSeasonWinner()

                ut.ADD_SEASON_INFO(division, temporada, season_data)
                #ut.SAVENOTTRANSFER()

                if enable_referees:
                    ut.SAVE_REFEREES_VALUES(args.referees_cache)

        # Guardado final de cachés y dataset consolidado
        print(f"\n{Fore.YELLOW}Guardando datos finales...{Style.RESET_ALL}")
        if enable_referees:
            ut.SAVE_REFEREES_VALUES(args.referees_cache)
        if enable_market:
            ut.SAVE_MARKET_VALUES(args.market_cache)

        ut.SAVE_ALL_SEASONS(args.output)

        elapsed = time.time() - start_time
        num_partidos = ut.CURRENT_MATCH_ID - 1
        num_equipos = len(ut.IDs_TO_TEAM)

        print(f"\n{Fore.GREEN}{Style.BRIGHT}[OK] PROCESO COMPLETADO CON EXITO!{Style.RESET_ALL}")
        print(f"* Total partidos procesados: {Fore.YELLOW}{num_partidos}{Style.RESET_ALL}")
        print(f"* Total equipos identificados: {Fore.YELLOW}{num_equipos}{Style.RESET_ALL}")
        print(f"* Dataset generado en: {Fore.GREEN}{os.path.abspath(args.output)}{Style.RESET_ALL}")
        print(f"* Tiempo empleado: {elapsed:.2f} segundos\n")

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Proceso interrumpido por el usuario.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error durante la ejecución: {e}{Style.RESET_ALL}")
        raise


if __name__ == "__main__":
    main()
