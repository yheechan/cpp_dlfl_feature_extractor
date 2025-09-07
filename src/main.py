import argparse
import logging
import os
from dotenv import load_dotenv

from lib.experiment_configs import ExperimentConfigs
from lib.factories.engine_factory import EngineFactory
from lib.factories.worker_factory import WorkerFactory
from lib.engines.engine import Engine
from lib.workers.worker import Worker

from utils.file_utils import *

def configurate_directories(config: ExperimentConfigs):
    cwd = os.getcwd()
    config.CWD = cwd
    root_dir = os.path.dirname(cwd)
    config.ROOT_DIR = root_dir
    home_dir = os.path.dirname(root_dir)
    config.HOME_DIR = home_dir
    config.RESEARCH_DATA = os.environ["RESEARCH_DATA"]

    def _configurate_log_dir():
        log_dir = os.path.join(config.ROOT_DIR, "logs", config.ARGS.experiment_label)
        config.LOG_DIR = log_dir
        make_directory(log_dir)

    def _configurate_data_dir():
        if "RESEARCH_DATA" not in os.environ:
            raise KeyError("RESEARCH_DATA environment variable not set.")
        research_data_dir = os.path.join(config.RESEARCH_DATA, config.ARGS.experiment_label)
        make_directory(research_data_dir)
    
    def _configurate_working_dir():
        working_dir = os.path.join(config.HOME_DIR, "cpp_research_working_dir", config.ARGS.experiment_label, config.ARGS.subject)
        config.WORKING_DIR = working_dir
        make_directory(working_dir)
    
    # Set default log directory
    _configurate_log_dir()

    # Set default research data directory
    _configurate_data_dir()

    # Set default working directory
    _configurate_working_dir()

def configurate_logger(config: ExperimentConfigs):
    main_log_file = os.path.join(config.LOG_DIR, "main.log")
    
    if config.ARGS.debug:
        log_level = logging.DEBUG
    elif config.ARGS.verbose:
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

def inital_configuration(config: ExperimentConfigs):
    load_dotenv(override=True)
    configurate_directories(config)
    configurate_logger(config)


def main():
    config = ExperimentConfigs()
    config.set_parser()

    inital_configuration(config)

    # Validate that only one of engine-type or worker-type is specified
    if config.ARGS.engine_type and config.ARGS.worker_type:
        logging.error("Cannot specify both --engine-type and --worker-type. Choose one.")
        return

    if not config.ARGS.engine_type and not config.ARGS.worker_type:
        logging.warning("No engine or worker type specified. Use -et/--engine-type or -wt/--worker-type.")
        logging.info(f"Available engines: {', '.join(EngineFactory.get_available_engines())}")
        logging.info(f"Available workers: {', '.join(WorkerFactory.get_available_workers())}")
        return

    # Handle engine execution
    if config.ARGS.engine_type:
        try:
            engine: Engine = EngineFactory.create_engine(
                config
            )
            logging.info(f"Successfully created engine: {config.ARGS.engine_type}")

            # Run the engine
            engine.run()
            
            # Clean up
            engine.cleanup()
            
        except ValueError as e:
            logging.error(f"Failed to create engine: {e}")
            available_engines = EngineFactory.get_available_engines()
            logging.info(f"Available engines: {', '.join(available_engines)}")
        except Exception as e:
            logging.error(f"Error running engine: {e}")
    
    # Handle worker execution
    if config.ARGS.worker_type:
        try:
            worker: Worker = WorkerFactory.create_worker(
                config
            )
            logging.info(f"Successfully created worker: {config.ARGS.worker_type}")

            # Execute the worker
            worker.execute()
            
            # Stop/cleanup
            worker.stop()
            
        except ValueError as e:
            logging.error(f"Failed to create worker: {e}")
            available_workers = WorkerFactory.get_available_workers()
            logging.info(f"Available workers: {', '.join(available_workers)}")
        except Exception as e:
            logging.error(f"Error running worker: {e}")


if __name__ == "__main__":
    main()