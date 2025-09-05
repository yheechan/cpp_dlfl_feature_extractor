import argparse
import logging
import os
from dotenv import load_dotenv

from lib.factories.engine_factory import EngineFactory
from lib.engines.engine import Engine

def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="C++ Deep-Learning-Based FL Feature Extractor"
    )

    # Logging and Debugging Options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increase output verbosity"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    # Function Selection
    parser.add_argument(
        "-et", "--engine-type",
        type=str,
        help="Specify the engine type to execute"
    )

    return parser

def configurate_directories():
    cwd = os.getcwd()
    os.environ["CWD"] = cwd
    home_dir = os.path.dirname(cwd)
    os.environ["HOME_DIR"] = home_dir

    def _configurate_log_dir():
        log_dir = os.path.join(home_dir, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        os.environ["LOG_DIR"] = log_dir

    def _configurate_data_dir():
        if "RESEARCH_DATA" not in os.environ:
            raise KeyError("RESEARCH_DATA environment variable not set.")
        research_data_dir = os.environ["RESEARCH_DATA"]
        if not os.path.exists(research_data_dir):
            os.makedirs(research_data_dir)
    
    # Set default log directory
    _configurate_log_dir()

    # Set default research data directory
    _configurate_data_dir()

def configurate_logger(args: argparse.Namespace):
    main_log_file = os.path.join(os.environ["LOG_DIR"], "main.log")
    
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.getLogger().setLevel(log_level)

    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s - %(asctime)s] %(filename)s::%(funcName)s - %(message)s",
        handlers=[
            logging.FileHandler(main_log_file, mode='w'),
            logging.StreamHandler()
        ]
    )

def inital_configuration(args: argparse.Namespace):
    load_dotenv(override=True)
    configurate_directories()
    configurate_logger(args)


def main():
    parser = make_parser()
    args = parser.parse_args()

    inital_configuration(args)

    engine = EngineFactory(engine_type=args.engine_type).create_engine()


if __name__ == "__main__":
    main()