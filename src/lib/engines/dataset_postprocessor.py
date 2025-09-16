import os
import logging
import pickle
import random

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.postprocessor_utils import *

LOGGER = logging.getLogger(__name__)

class DatasetPostprocessor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        # Additional initialization for DatasetPostprocessor if needed
        self._initialize_required_directories()

    def run(self):
        """Run the dataset postprocessing steps"""
        LOGGER.info("Running DatasetPostprocessor...")

        self._process_dataset()
    
    def _initialize_required_directories(self):
        self.config_dir = os.path.join(
            self.CONFIG.ENV["ROOT_DIR"],
            "configs"
        )

        self.set_experiment_setup_configs()

        self.constructed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "constructed_dataset"
        )

        self.posprocessed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "postprocessed_dataset"
        )
        self.FILE_MANAGER.make_directory(self.posprocessed_dataset_dir)
        LOGGER.info(f"Constructed dataset directory initialized at {self.posprocessed_dataset_dir}")

        self.statement_info_dir = os.path.join(self.posprocessed_dataset_dir, "statement_info")
        self.FILE_MANAGER.make_directory(self.statement_info_dir)
        LOGGER.info(f"Statement info directory initialized at {self.statement_info_dir}")

        for rid in range(1, self.CONFIG.ENV["num_repeats"]+1):
            test_dir = os.path.join(self.posprocessed_dataset_dir, f"repeat_{rid}/test_dataset")
            self.FILE_MANAGER.make_directory(test_dir)

            for line_cnt in self.CONFIG.ENV["target_lines"]:
                for mut_cnt in self.CONFIG.ENV["mutation_cnt"]:
                    method_dir = os.path.join(self.posprocessed_dataset_dir, f"repeat_{rid}/lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{self.CONFIG.ENV['tcs_reduction']}")
                    self.FILE_MANAGER.make_directory(method_dir)

    def _process_dataset(self):
        statement_data = {}
        faulty_statement_data = {}

        statements_pkl = os.path.join(self.statement_info_dir, "statements.pkl")
        if os.path.exists(statements_pkl):
            with open(statements_pkl, 'rb') as f:
                statement_data = pickle.load(f)
            LOGGER.debug(f"Loaded existing statements from {statements_pkl}")
        else:
            LOGGER.debug(f"Statements file {statements_pkl} does not exist, starting with empty statement data.")

        faulty_statements_pkl = os.path.join(self.statement_info_dir, "faulty_statement_set.pkl")
        if os.path.exists(faulty_statements_pkl):
            with open(faulty_statements_pkl, 'rb') as f:
                faulty_statement_data = pickle.load(f)
            LOGGER.debug(f"Loaded existing faulty statements from {faulty_statements_pkl}")
        else:
            LOGGER.debug(f"Faulty statements file {faulty_statements_pkl} does not exist, starting with empty faulty statement data.")

        for rid in range(1, self.CONFIG.ENV["num_repeats"] + 1):
            pp_data = {}
            pp_data["test_dataset"] = {"x": {}, "y": {}}
            dataset_pkl = os.path.join(self.constructed_dataset_dir, f"repeat_{rid}/dataset.pkl")
            if os.path.exists(dataset_pkl) and False:
                pp_data = pickle.load(open(dataset_pkl, 'rb'))
                LOGGER.debug(f"Loaded existing dataset for repeat {rid} from {dataset_pkl}")
            else:
                LOGGER.debug(f"Creating new dataset for repeat {rid}")
            
            # Over all subject, set dataset for both test and different methods
            #iterate through directory of self.constructed_dataset_dir, these are the dataset for each subject
            for subject_dataset_dir in os.listdir(self.constructed_dataset_dir):
                subject_name = os.path.basename(subject_dataset_dir)
                rid_key = f"repeat_{rid}"

                rid_dir = os.path.join(self.constructed_dataset_dir, subject_name, rid_key)
                if not os.path.exists(rid_dir):
                    LOGGER.warning(f"Directory {rid_dir} does not exist.")
                    raise FileNotFoundError(f"Directory {rid_dir} does not exist.")
                
                # For each fault (bid) in the subject
                for bid_pkl_file_name in os.listdir(rid_dir):
                    # e.g., bug95--adler32_avx2.MUT18.c--lineIdx2lineData.pkl
                    bid = int(bid_pkl_file_name.split("--")[0].replace("bug", ""))
                    # if bid != 1: continue
                    full_fault_id = f"{subject_name}_{bid}"
                    bid_pkl_file = os.path.join(rid_dir, bid_pkl_file_name)

                    bid_data = normalize_data(bid_pkl_file, self.CONFIG.ENV)

                    #  Set the test dataset
                    set_statement_info = False
                    if full_fault_id not in statement_data:
                        set_statement_info = True
                        statement_data[full_fault_id] = []
                        faulty_statement_data[full_fault_id] = []

                    set_dataset(
                        pp_data["test_dataset"], full_fault_id, bid_data,
                        statement_data=statement_data, 
                        faulty_statement_data=faulty_statement_data,
                        lnc=self.CONFIG.ENV["target_lines"][-1],  # Use the last line count for test dataset
                        mtc=self.CONFIG.ENV["mutation_cnt"][-1],  # Use the last mutation count for test dataset
                        tcr="Reduced",  # Use "Reduced" for test dataset
                        set_statement_info=set_statement_info
                    )

                    # Set for diff. methods
                    set_for_methods(pp_data, bid_data, full_fault_id, self.CONFIG.ENV)
            
            # Divide dataset into test, train, validation set using proper 10-fold CV
            versions = list(pp_data["test_dataset"]["x"].keys())
            self.divide_dataset(pp_data, versions, rid)
        
        # Save the statement information
        self.save_stmt_info(statement_data, faulty_statement_data)

    def divide_dataset(self, pp_data, versions, rid, train_val_split=0.9):
        random.seed(888)
        random.shuffle(versions)
        total_versions = len(versions)
        LOGGER.info(f"Total versions: {total_versions}")
        
        # Calculate fold sizes for 10-fold CV
        base_fold_size = total_versions // 10
        extra_versions = total_versions % 10
        
        # Create fold sizes: some folds will have base_fold_size+1, others base_fold_size
        fold_sizes = [base_fold_size + (1 if i < extra_versions else 0) for i in range(10)]
        LOGGER.info(f"Fold sizes: {fold_sizes} (total: {sum(fold_sizes)})")

        dataset_pkl = os.path.join(self.posprocessed_dataset_dir, f"repeat_{rid}/dataset.pkl")
        with open(dataset_pkl, 'wb') as f:
            pickle.dump(pp_data, f)

        # Create fold boundaries
        fold_boundaries = [0]
        for size in fold_sizes:
            fold_boundaries.append(fold_boundaries[-1] + size)

        for method_name, data in pp_data.items():
            LOGGER.info(f"Processing method: {method_name}")

            # For each k-fold group
            for group_index in range(10):
                # Get test versions for this fold
                start_idx = fold_boundaries[group_index]
                end_idx = fold_boundaries[group_index + 1]
                test_versions = versions[start_idx:end_idx]
                train_versions = [v for v in versions if v not in test_versions]

                LOGGER.info(f"\tGroup {group_index + 1}: {len(test_versions)} test versions, {len(train_versions)} train versions")

                # Collect training data from all training versions
                train_pos_x = []
                train_neg_x = []

                for version in train_versions:
                    if version not in data["x"] or version not in data["y"]:
                        LOGGER.warning(f"Version {version} not found in data for method {method_name}")
                        raise ValueError(f"Version {version} not found in data for method {method_name}")
                        
                    pos_indices = [i for i, y in enumerate(data["y"][version]) if y == 0]
                    neg_indices = [i for i, y in enumerate(data["y"][version]) if y == 1]
                    assert len(pos_indices) + len(neg_indices) == len(data["y"][version]), "Mismatch in indices and labels length"

                    # Set Training Dataset: 10 negative samples for each positive sample
                    for pos_idx, pos_index in enumerate(pos_indices):
                        
                        # Sample 10 negative examples for this positive example
                        # Use deterministic seed based on version and position for consistency across methods
                        seed_value = hash(f"{version}_{pos_idx}_{rid}_{group_index}") % (2**31)
                        random.seed(seed_value)
                        shuffled_neg_indices = neg_indices.copy()
                        random.shuffle(shuffled_neg_indices)
                        
                        for neg_index in shuffled_neg_indices[:min(10, len(shuffled_neg_indices))]:
                            train_pos_x.append(data["x"][version][pos_index])
                            train_neg_x.append(data["x"][version][neg_index])
                
                # Create test dataset for this fold
                test_x = {}
                test_y = {}
                for version in test_versions:
                    if version in data["x"] and version in data["y"]:
                        test_x[version] = data["x"][version]
                        test_y[version] = data["y"][version]
                
                # Shuffle training data with deterministic seeds
                random.seed(hash(f"train_pos_{rid}_{group_index}") % (2**31))
                random.shuffle(train_pos_x)
                random.seed(hash(f"train_neg_{rid}_{group_index}") % (2**31))
                random.shuffle(train_neg_x)

                # Divide into train and validation sets
                val_split_pos = round(len(train_pos_x) * train_val_split)
                val_split_neg = round(len(train_neg_x) * train_val_split)
                
                val_pos_x = train_pos_x[val_split_pos:]
                val_neg_x = train_neg_x[val_split_neg:]

                train_pos_x = train_pos_x[:val_split_pos]
                train_neg_x = train_neg_x[:val_split_neg]
                
                LOGGER.info(f"\tGroup {group_index + 1}: Train pos: {len(train_pos_x)}, Train neg: {len(train_neg_x)}, Val pos: {len(val_pos_x)}, Val neg: {len(val_neg_x)}")
                
                # Set the dataset group directory
                if method_name == "test_dataset":
                    group_dir = os.path.join(self.posprocessed_dataset_dir, f"repeat_{rid}/test_dataset/group_{group_index + 1}")
                else:
                    group_dir = os.path.join(self.posprocessed_dataset_dir, f"repeat_{rid}/methods/{method_name}/group_{group_index + 1}")
                
                if not os.path.exists(group_dir):
                    os.makedirs(group_dir, exist_ok=True)

                # Make directories for train, val, and test
                train_dir = f"{group_dir}/train"
                val_dir = f"{group_dir}/val"
                test_dir = f"{group_dir}/test"
                
                for dir_path in [train_dir, val_dir, test_dir]:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)

                # Save training data
                with open(os.path.join(train_dir, "x_pos.pkl"), 'wb') as f:
                    pickle.dump(train_pos_x, f)
                with open(os.path.join(train_dir, "x_neg.pkl"), 'wb') as f:
                    pickle.dump(train_neg_x, f)

                # Save validation data
                with open(os.path.join(val_dir, "x_pos.pkl"), 'wb') as f:
                    pickle.dump(val_pos_x, f)
                with open(os.path.join(val_dir, "x_neg.pkl"), 'wb') as f:
                    pickle.dump(val_neg_x, f)

                # Save test data
                with open(os.path.join(test_dir, "x.pkl"), 'wb') as f:
                    pickle.dump(test_x, f)
                with open(os.path.join(test_dir, "y.pkl"), 'wb') as f:
                    pickle.dump(test_y, f)            

    def save_stmt_info(self, statement_data, faulty_statement_data):
        """
        Save the statement information as pkl files.
        """
        if not os.path.exists(self.statement_info_dir):
            os.makedirs(self.statement_info_dir, exist_ok=True)

        # Save statement data
        with open(os.path.join(self.statement_info_dir, "statements.pkl"), 'wb') as f:
            pickle.dump(statement_data, f)
        
        # Save faulty statement data
        with open(os.path.join(self.statement_info_dir, "faulty_statement_set.pkl"), 'wb') as f:
            pickle.dump(faulty_statement_data, f)

    def cleanup(self):
        """Clean up resources used by the dataset constructor"""
        LOGGER.info("Cleaning up DatasetPostprocessor resources")
        super().cleanup()
