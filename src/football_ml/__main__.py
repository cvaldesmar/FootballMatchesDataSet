"""CLI del pipeline de aprendizaje automático."""

from __future__ import annotations

import argparse
import json
from datetime import date

from .evaluate import evaluate_by_season, evaluate_model
from .io import load_ml_dataset
from .next_round import run_next_round
from .predict import predict_csv
from .train import load_artifact, train_model
from .tuning import tune_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline ML para resultados 1X2")
    commands = parser.add_subparsers(dest="command", required=True)

    train = commands.add_parser("train", help="Entrena y persiste un modelo")
    train.add_argument("--input", required=True)
    train.add_argument("--model", required=True)
    train.add_argument(
        "--model-name",
        choices=["logistic", "random-forest", "gradient-boosting", "xgboost", "lightgbm"],
        default="logistic",
    )
    _add_selection_arguments(train)
    train.add_argument("--test-seasons", type=int, default=2)
    train.add_argument("--validation-seasons", type=int, default=1)

    evaluate = commands.add_parser("evaluate", help="Evalúa un modelo persistido")
    evaluate.add_argument("--input", required=True)
    evaluate.add_argument("--model", required=True)
    evaluate.add_argument("--by-season", action="store_true")

    predict = commands.add_parser("predict", help="Predice filas de un CSV")
    predict.add_argument("--model", required=True)
    predict.add_argument("--input", required=True)
    predict.add_argument("--output")
    compare = commands.add_parser("compare", help="Compara estrategias 1X2 con walk-forward")
    compare.add_argument("--input", required=True)
    compare.add_argument(
        "--strategies",
        nargs="+",
        choices=["multiclass", "staged", "poisson"],
        default=["multiclass", "staged", "poisson"],
    )
    compare.add_argument("--min-train-rounds", type=int, default=10)
    compare.add_argument("--max-validation-rounds", type=int)
    _add_selection_arguments(compare)

    tune = commands.add_parser("tune", help="Optimiza modelos e hiperparámetros con walk-forward")
    tune.add_argument("--input", required=True)
    tune.add_argument("--model", required=True)
    tune.add_argument(
        "--models",
        nargs="+",
        default=["logistic", "random-forest", "gradient-boosting", "xgboost", "lightgbm"],
        choices=["logistic", "random-forest", "gradient-boosting", "xgboost", "lightgbm"],
    )
    tune.add_argument("--trials-per-model", type=int, default=20)
    tune.add_argument("--min-train-rounds", type=int, default=10)
    tune.add_argument("--max-validation-rounds", type=int)
    tune.add_argument("--max-train-rounds", type=int)
    _add_selection_arguments(tune)

    next_round = commands.add_parser("next-round", help="Predice la próxima jornada sin resultados")
    next_round.add_argument("--history", required=True)
    next_round.add_argument("--fixtures", required=True)
    next_round.add_argument("--model", required=True)
    next_round.add_argument("--as-of", required=True, help="Fecha de corte YYYY-MM-DD")
    next_round.add_argument("--output")
    next_round.add_argument(
        "--model-name",
        choices=["logistic", "random-forest", "gradient-boosting", "xgboost", "lightgbm"],
        default="logistic",
    )
    next_round.add_argument(
        "--retrain",
        action="store_true",
        help="Ignora el modelo existente y reentrena; no ejecuta Optuna automáticamente",
    )
    _add_selection_arguments(next_round)
    return parser


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--min-season", default="2000-01")
    group.add_argument("--last-seasons", type=int)


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "compare":
        from .selection import select_recent
        from .strategies import strategy_factory
        from .walk_forward import walk_forward_evaluate

        frame = load_ml_dataset(args.input)
        selected, _ = select_recent(
            frame, min_season=args.min_season, last_seasons=args.last_seasons
        )
        comparison = {}
        for strategy in args.strategies:
            result = walk_forward_evaluate(
                selected,
                train_step=strategy_factory(strategy),
                min_train_rounds=args.min_train_rounds,
                max_validation_rounds=args.max_validation_rounds,
            )
            comparison[strategy] = result.metrics
        print(json.dumps(comparison, ensure_ascii=False, indent=2))
    elif args.command == "tune":
        frame = load_ml_dataset(args.input)
        selected, _ = __import__(
            "src.football_ml.selection", fromlist=["select_recent"]
        ).select_recent(frame, min_season=args.min_season, last_seasons=args.last_seasons)
        artifact = tune_catalog(
            selected,
            tuple(args.models),
            n_trials=args.trials_per_model,
            min_train_rounds=args.min_train_rounds,
            max_validation_rounds=args.max_validation_rounds,
            max_train_rounds=args.max_train_rounds,
            output_path=args.model,
        )
        print(
            json.dumps(
                {
                    "model_name": artifact["model_name"],
                    "params": artifact["params"],
                    "walk_forward_metrics": artifact["walk_forward_metrics"],
                    "catalog_results": artifact["catalog_results"],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    elif args.command == "train":
        artifact = train_model(
            load_ml_dataset(args.input),
            args.model,
            model_name=args.model_name,
            min_season=args.min_season,
            last_seasons=args.last_seasons,
            test_seasons=args.test_seasons,
            validation_seasons=args.validation_seasons,
        )
        print(
            json.dumps(
                {key: artifact[key] for key in ("model_name", "selection", "test_metrics")},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "evaluate":
        artifact = load_artifact(args.model)
        frame = load_ml_dataset(args.input)
        metrics = (
            evaluate_by_season(artifact["model"], frame)
            if args.by_season
            else evaluate_model(artifact["model"], frame)
        )
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    elif args.command == "predict":
        result = predict_csv(args.model, args.input, args.output)
        print(result.to_json(orient="records", force_ascii=False, indent=2))
    else:
        result, artifact = run_next_round(
            args.history,
            args.fixtures,
            args.model,
            as_of=date.fromisoformat(args.as_of),
            min_season=args.min_season,
            last_seasons=args.last_seasons,
            model_name=args.model_name,
            output_path=args.output,
            retrain=args.retrain,
        )
        print(
            json.dumps(
                {
                    "predictions": result.to_dict("records"),
                    "model_name": artifact["model_name"],
                    "selection": artifact["selection"],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
