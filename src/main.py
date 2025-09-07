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

def configurate_directories(CONFIG: ExperimentConfigs):
    cwd = os.getcwd()
    CONFIG.CWD = cwd
    root_dir = os.path.dirname(cwd)
    CONFIG.ROOT_DIR = root_dir
    home_dir = os.path.dirname(root_dir)
    CONFIG.HOME_DIR = home_dir
    CONFIG.RESEARCH_DATA = os.environ["RESEARCH_DATA"]

def configurate_logger(CONFIG: ExperimentConfigs):
    log_dir = os.path.join(
        CONFIG.ROOT_DIR, 
        "logs",
        CONFIG.ARGS.experiment_label,
        CONFIG.ARGS.subject
    )
    make_directory(log_dir)

    main_log_file = os.path.join(log_dir, "main.log")
    
    if CONFIG.ARGS.debug:
        log_level = logging.DEBUG
    elif CONFIG.ARGS.verbose:
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

def initial_configuration(config: ExperimentConfigs):
    load_dotenv(override=True)
    configurate_directories(config)
    configurate_logger(config)


def main():
    CONFIG = ExperimentConfigs()
    CONFIG.set_parser()

    initial_configuration(CONFIG)

    # Validate that only one of engine-type or worker-type is specified
    if CONFIG.ARGS.engine_type and CONFIG.ARGS.worker_type:
        logging.error("Cannot specify both --engine-type and --worker-type. Choose one.")
        return

    if not CONFIG.ARGS.engine_type and not CONFIG.ARGS.worker_type:
        logging.warning("No engine or worker type specified. Use -et/--engine-type or -wt/--worker-type.")
        logging.info(f"Available engines: {', '.join(EngineFactory.get_available_engines())}")
        logging.info(f"Available workers: {', '.join(WorkerFactory.get_available_workers())}")
        return

    # Handle engine execution
    if CONFIG.ARGS.engine_type:
        try:
            engine: Engine = EngineFactory.create_engine(CONFIG)
            logging.info(f"Successfully created engine: {CONFIG.ARGS.engine_type}")

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
    if CONFIG.ARGS.worker_type:
        try:
            worker: Worker = WorkerFactory.create_worker(CONFIG)
            logging.info(f"Successfully created worker: {CONFIG.ARGS.worker_type}")

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