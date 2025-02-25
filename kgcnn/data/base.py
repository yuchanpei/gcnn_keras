import logging
import numpy as np
import tensorflow as tf
import pandas as pd
import os
from typing import Union, List, Callable
from collections.abc import MutableMapping
from kgcnn.data.utils import save_pickle_file, load_pickle_file, ragged_tensor_from_nested_numpy
from kgcnn.graph.base import GraphDict

logging.basicConfig()  # Module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.INFO)


class MemoryGraphList(MutableMapping):
    r"""Class to store a list of graph dictionaries in memory.

    Contains a python list as property :obj:`_list`. The graph properties are defined by tensor-like (numpy) arrays
    for indices, attributes, labels, symbol etc. in :obj:`GraphDict`, which are the items of the list.
    Access to items via `[]` indexing operator.

    A python list of a single named property can be obtained from each :obj:`GraphDict` in :obj:`MemoryGraphList` via
    :obj:`get` or assigned from a python list via :obj:`set` methods.

    The :obj:`MemoryGraphList` further provides simple map-functionality :obj:`map_list` to apply methods for
    each :obj:`GraphDict`, and to cast properties to tensor with :obj:`tensor`.

    Cleaning the list for missing properties or empty graphs is done with :obj:`clean`.

    .. code-block:: python

        import numpy as np
        from kgcnn.data.base import MemoryGraphList

        data = MemoryGraphList()
        data.empty(1)
        data.set("edge_indices", [np.array([[0, 1], [1, 0]])])
        data.set("node_labels", [np.array([[0], [1]])])
        print(data.get("edge_indices"))
        data.set("node_coordinates", [np.array([[1, 0, 0], [0, 1, 0], [0, 2, 0], [0, 3, 0]])])
        data.map_list("set_range", max_distance=1.5, max_neighbours=10, self_loops=False)
        data.clean("range_indices")  # Returns cleaned graph indices
        print(len(data))
        print(data[0])
    """

    def __init__(self, input_list: list = None):
        r"""Initialize an empty :obj:`MemoryGraphList` instance.

        Args:
            input_list (list, MemoryGraphList): A list or :obj:`MemoryGraphList` of :obj:`GraphDict` items.
        """
        self._list = []
        self.logger = module_logger
        if input_list is None:
            input_list = []
        if isinstance(input_list, list):
            self._list = [GraphDict(x) for x in input_list]
        if isinstance(input_list, MemoryGraphList):
            self._list = [GraphDict(x) for x in input_list._list]

    def assign_property(self, key: str, value: list):
        """Assign a list of numpy arrays of a property to :obj:`GraphDict`s in this list.

        Args:
            key (str): Name of the property.
            value (list): List of numpy arrays for property `key`.

        Returns:
            self
        """
        if value is None:
            # We could also here remove the key from all graphs.
            return self
        if not isinstance(value, list):
            raise TypeError("Expected type 'list' to assign graph properties.")
        if len(self._list) == 0:
            self.empty(len(value))
        if len(self._list) != len(value):
            raise ValueError("Can only store graph attributes from list with same length.")
        for i, x in enumerate(value):
            self._list[i].assign_property(key, x)
        return self

    def obtain_property(self, key: str) -> Union[list, None]:
        r"""Returns a list with the values of all the graphs defined for the string property name `key`. If none of
        the graphs in the list have this property, returns None.

        Args:
            key (str): The string name of the property to be retrieved for all the graphs contained in this list
        """
        # "_list" is a list of GraphDicts, which means "prop_list" here will be a list of all the property
        # values for teach of the graphs which make up this list.
        prop_list = [x.obtain_property(key) for x in self._list]

        # If a certain string property is not set for a GraphDict, it will still return None. Here we check:
        # If all the items for our given property name are None then we know that this property is generally not
        # defined for any of the graphs in the list.
        if all([x is None for x in prop_list]):
            self.logger.warning("Property %s is not set on any graph." % key)
            return None

        return prop_list

    def __len__(self):
        """Return the current length of this instance."""
        return len(self._list)

    def __getitem__(self, item):
        # Does not make a copy of the data, as a python list does.
        if isinstance(item, int):
            return self._list[item]
        new_list = MemoryGraphList()
        if isinstance(item, slice):
            return new_list._set_internal_list(self._list[item])
        if isinstance(item, list):
            return new_list._set_internal_list([self._list[int(i)] for i in item])
        if isinstance(item, np.ndarray):
            return new_list._set_internal_list([self._list[int(i)] for i in item])
        raise TypeError("Unsupported type for `MemoryGraphList` items.")

    def __setitem__(self, key, value):
        if not isinstance(value, GraphDict):
            raise TypeError("Require a GraphDict as list item.")
        self._list[key] = value

    def __delitem__(self, key):
        value = self._list.__delitem__(key)
        return value

    def __iter__(self):
        return iter(self._list)

    def _set_internal_list(self, value: list):
        if not isinstance(value, list):
            raise TypeError("Must set list for `MemoryGraphList` internal assignment.")
        self._list = value
        return self

    def clear(self):
        """Clear internal list.

        Returns:
            None
        """
        self._list.clear()

    def empty(self, length: int):
        """Create an empty list in place. Overwrites existing list.

        Args:
            length (int): Length of the empty list.

        Returns:
            self
        """
        if length is None:
            return self
        if length < 0:
            raise ValueError("Length of empty list must be >=0.")
        self._list = [GraphDict() for _ in range(length)]
        return self

    @property
    def length(self):
        """Length of list."""
        return len(self._list)

    @length.setter
    def length(self, value: int):
        raise ValueError("Can not set length. Please use 'empty()' to initialize an empty list.")

    def _to_tensor(self, item, make_copy=True):
        if not make_copy:
            self.logger.warning("At the moment always a copy is made for tensor().")
        props = self.obtain_property(item["name"])  # Will be list.
        is_ragged = item["ragged"] if "ragged" in item else False
        if is_ragged:
            return ragged_tensor_from_nested_numpy(props)
        else:
            return tf.constant(np.array(props))

    def tensor(self, items: Union[list, dict], make_copy=True):
        r"""Make tensor objects from multiple graph properties in list.

        It is recommended to run :obj:`clean` beforehand.

        Args:
            items (list): List of dictionaries that specify graph properties in list via 'name' key.
                The dict-items match the tensor input for :obj:`tf.keras.layers.Input` layers.
                Required dict-keys should be 'name' and 'ragged'.
                Optionally shape information can be included via 'shape'.
                E.g.: `[{'name': 'edge_indices', 'ragged': True}, {...}, ...]`.
            make_copy (bool): Whether to copy the data. Default is True.

        Returns:
            list: List of Tensors.
        """
        if isinstance(items, dict):
            return self._to_tensor(items, make_copy=make_copy)
        elif isinstance(items, (tuple, list)):
            return [self._to_tensor(x, make_copy=make_copy) for x in items]
        else:
            raise TypeError("Wrong type, expected e.g. [{'name': 'edge_indices', 'ragged': True}, {...}, ...]")

    def map_list(self, method: Union[str, Callable], **kwargs):
        r"""Map a method over this list and apply on each :obj:`GraphDict`.
        For :obj:`method` being string, either a class-method or a preprocessor is chosen for backward compatibility.

        .. code-block:: python

            for i, x in enumerate(self):
                method(x, **kwargs)

        Args:
            method (str): Name of the :obj:`GraphDict` method.
            kwargs: Kwargs for `method`.

        Returns:
            self
        """
        # Can add progress info here.
        # Method by name.
        if isinstance(method, str):
            for i, x in enumerate(self._list):
                # If this is a class method.
                if hasattr(x, method):
                    getattr(x, method)(**kwargs)
                else:
                    # For compatibility names can refer to preprocessors.
                    x.apply_preprocessor(name=method, **kwargs)
        elif isinstance(method, dict):
            raise NotImplementedError("Serialization for method in `map_list` is not yet supported")
        else:
            # For any callable method to map.
            for i, x in enumerate(self._list):
                method(x, **kwargs)
        return self

    def clean(self, inputs: Union[list, str]):
        r"""Given a list of property names, this method removes all elements from the internal list of
        `GraphDict` items, which do not define at least one of those properties. Meaning, only those graphs remain in
        the list which definitely define all properties specified by :obj:`inputs`.

        Args:
            inputs (list): A list of strings, where each string is supposed to be a property name, which the graphs
                in this list may possess. Within :obj:`kgcnn`, this can be simpy the 'input' category in model
                configuration. In this case, a list of dicts that specify the name of the property with 'name' key.

        Returns:
            invalid_graphs (np.ndarray): A list of graph indices that do not have the required properties and which
                have been removed.
        """
        if isinstance(inputs, str):
            inputs = [inputs]
        invalid_graphs = []
        for item in inputs:
            # If this is a list of dict, which are the config for ks.layers.Input(), we pick 'name'.
            if isinstance(item, dict):
                item_name = item["name"]
            else:
                item_name = item
            props = self.obtain_property(item_name)
            if props is None:
                self.logger.warning("Can not clean property %s as it was not assigned to any graph." % item)
                continue
            for i, x in enumerate(props):
                # If property is neither list nor np.array
                if x is None or not hasattr(x, "__getitem__"):
                    self.logger.info("Property %s is not defined for graph %s." % (item_name, i))
                    invalid_graphs.append(i)
                elif not isinstance(x, np.ndarray):
                    self.logger.info("Property %s is not a numpy array for graph %s." % (item_name, i))
                    invalid_graphs.append(i)
                elif len(x.shape) > 0:
                    if len(x) <= 0:
                        self.logger.info("Property %s is an empty list for graph %s." % (item_name, i))
                        invalid_graphs.append(i)
        invalid_graphs = np.unique(np.array(invalid_graphs, dtype="int"))
        invalid_graphs = np.flip(invalid_graphs)  # Need descending order for pop()
        if len(invalid_graphs) > 0:
            self.logger.warning("Found invalid graphs for properties. Removing graphs %s." % invalid_graphs)
        else:
            self.logger.info("No invalid graphs for assigned properties found.")
        # Remove from the end via pop().
        for i in invalid_graphs:
            self._list.pop(int(i))
        return invalid_graphs

    # Alias of internal assign and obtain property.
    set = assign_property
    get = obtain_property


class MemoryGraphDataset(MemoryGraphList):
    r"""Dataset class for lists of graph tensor dictionaries stored on file and fit into memory.

    This class inherits from :obj:`MemoryGraphList` and can be used (after loading and setup) as such.
    It has further information about a location on disk, i.e. a file directory and a file
    name as well as a name of the dataset.

    .. code-block:: python

        from kgcnn.data.base import MemoryGraphDataset
        dataset = MemoryGraphDataset(data_directory="", dataset_name="Example")
        # Methods of MemoryGraphList
        dataset.set("edge_indices", [np.array([[1, 0], [0, 1]])])
        dataset.set("edge_labels", [np.array([[0], [1]])])
        dataset.save()

    The file directory and file name are used in child classes and in :obj:`save` and :obj:`load`.
    """

    fits_in_memory = True

    def __init__(self,
                 data_directory: str = None,
                 dataset_name: str = None,
                 file_name: str = None,
                 file_directory: str = None,
                 verbose: int = 10,
                 ):
        r"""Initialize a base class of :obj:`MemoryGraphDataset`.

        Args:
            data_directory (str): Full path to directory of the dataset. Default is None.
            file_name (str): Generic filename for dataset to read into memory like a 'csv' file. Default is None.
            file_directory (str): Name or relative path from :obj:`data_directory` to a directory containing sorted
                files. Default is None.
            dataset_name (str): Name of the dataset. Important for naming and saving files. Default is None.
            verbose (int): Logging level. Default is 10.
        """
        super(MemoryGraphDataset, self).__init__()
        # For logging.
        self.logger = logging.getLogger("kgcnn.data." + dataset_name) if dataset_name is not None else module_logger
        self.logger.setLevel(verbose)
        # Information on location of dataset on file. Data directory must be filepath.
        self.data_directory = data_directory
        self.file_name = file_name
        self.file_directory = file_directory
        self.dataset_name = dataset_name
        # Data Frame for labels and graph names.
        self.data_frame = None
        self.data_keys = None
        self.data_unit = None

    @property
    def file_path(self):
        r"""Construct filepath from 'file_name' given in `init`."""
        if self.data_directory is None:
            self.warning("Data directory is not set.")
            return None
        if not os.path.exists(os.path.realpath(self.data_directory)):
            self.error("Data directory does not exist.")
        if self.file_name is None:
            self.warning("Can not determine file path, missing `file_name`.")
            return None
        return os.path.join(self.data_directory, self.file_name)

    @property
    def file_directory_path(self):
        r"""Construct file-directory path from 'data_directory' and 'file_directory' given in `init`."""
        if self.data_directory is None:
            self.warning("Data directory is not set.")
            return None
        if not os.path.exists(self.data_directory):
            self.error("Data directory does not exist.")
        if self.file_directory is None:
            self.warning("Can not determine file directory, missing `file_directory`.")
            return None
        return os.path.join(self.data_directory, self.file_directory)

    def info(self, *args, **kwargs):
        """Pass information to class' logger instance."""
        self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        """Pass warning to class' logger instance."""
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        """Pass error to class' logger instance."""
        self.logger.error(*args, **kwargs)

    def save(self, filepath: str = None):
        r"""Save all graph properties to python dictionary as pickled file. By default, saves a file named
        :obj:`dataset_name.kgcnn.pickle` in :obj:`data_directory`.

        Args:
            filepath (str): Full path of output file. Default is None.
        """
        if filepath is None:
            filepath = os.path.join(self.data_directory, self.dataset_name + ".kgcnn.pickle")
        self.info("Pickle dataset...")
        save_pickle_file([x.to_dict() for x in self._list], filepath)
        return self

    def load(self, filepath: str = None):
        r"""Load graph properties from a pickled file. By default, loads a file named
        :obj:`dataset_name.kgcnn.pickle` in :obj:`data_directory`.

        Args:
            filepath (str): Full path of input file.
        """
        if filepath is None:
            filepath = os.path.join(self.data_directory, self.dataset_name + ".kgcnn.pickle")
        self.info("Load pickled dataset...")
        in_list = load_pickle_file(filepath)
        self._list = [GraphDict(x) for x in in_list]
        return self

    def read_in_table_file(self, file_path: str = None, **kwargs):
        r"""Read a data frame in :obj:`data_frame` from file path. By default, uses :obj:`file_name` and pandas.
        Checks for a '.csv' file and then for Excel file endings. Meaning the file extension of file_path is ignored
        but must be any of the following '.csv', '.xls', '.xlsx', '.odt'.

        Args:
            file_path (str): File path to table file. Default is None.
            kwargs: Kwargs for pandas :obj:`read_csv` function.

        Returns:
            self
        """
        if file_path is None:
            file_path = os.path.join(self.data_directory, self.file_name)

        # TODO: Better determine file-type from file ending and just test all supported types otherwise.
        # file_extension_given = os.path.splitext(file_path)[1]
        file_path_base = os.path.splitext(file_path)[0]

        for file_extension in [".csv"]:
            if os.path.exists(file_path_base + file_extension):
                self.data_frame = pd.read_csv(file_path_base + file_extension, **kwargs)
                return self
        for file_extension in [".xls", ".xlsx", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"]:
            if os.path.exists(file_path_base + file_extension):
                self.data_frame = pd.read_excel(file_path_base + file_extension, **kwargs)
                return self

        self.warning("Unsupported data extension of '%s' for table file." % file_path)
        return self

    def assert_valid_model_input(self, hyper_input: Union[list, dict], raise_error_on_fail: bool = True):
        r"""Check whether dataset has graph properties (in tensor format) requested by model input.

        The list :obj:`hyper_input` that defines model input match interface to hyperparameter.
        The model input is set up by a list of layer configs for the keras :obj:`Input` layer.
        The list must contain dictionaries for each model input with "name" and "shape" keys.

        .. code-block:: python

            hyper_input = [
                {"shape": [None, 8710], "name": "node_attributes", "dtype": "float32", "ragged": True},
                {"shape": [None, 1], "name": "edge_weights", "dtype": "float32", "ragged": True},
                {"shape": [None, 2], "name": "edge_indices", "dtype": "int64", "ragged": True}
            ]

        Args:
            hyper_input (list): List of properties that need to be available to a model for training.
            raise_error_on_fail (bool): Whether to raise an error if assertion failed.
        """
        dataset = self

        def message_error(msg):
            if raise_error_on_fail:
                raise ValueError(msg)
            else:
                dataset.error(msg)

        def message_warning(msg):
            dataset.warning(msg)

        if isinstance(hyper_input, dict):
            if "name" in hyper_input and "shape" in hyper_input:
                # Single model input that has not been properly passed as list.
                # Assume here one does not name model output name and shape.
                hyper_input = [hyper_input]
            else:
                # In principle keras also accepts a dictionary for model inputs. Just cast to list here.
                hyper_input = list(hyper_input.values())

        # Check if we have List[dict].
        for x in hyper_input:
            if not isinstance(x, dict):
                message_error(
                    "Wrong type of list item in `assert_valid_model_input`. Found %s but must be `dict`" % type(x))

        for x in hyper_input:
            if "name" not in x:
                message_error("Can not infer name from '%s' for model input." % x)
            data = [dataset[i].obtain_property(x["name"]) for i in range(len(dataset))]
            prop_in_data = [y is None for y in data]
            if all(prop_in_data):
                message_error("Property %s is not defined for any graph in list. Please check property." % x["name"])
            if any(prop_in_data):
                message_warning("Property %s is not defined for all graphs in list. Please run clean()." % x["name"])

            # we also will check shape here but only with first element.
            if hasattr(data[0], "shape") and "shape" in x:
                shape_element = data[0].shape
                shape_input = x["shape"]
                if len(shape_input) != len(shape_element):
                    message_error(
                        "Mismatch in rank for model input {} vs. {}".format(shape_element, shape_input))
                for i, dim in enumerate(shape_input):
                    if dim is not None:
                        if shape_element[i] != dim:
                            message_error(
                                "Mismatch in shape for model input {} vs. {}".format(shape_element, shape_input))
            else:
                message_error("Can not check shape for '%s'." % x["name"])
        return

    def collect_files_in_file_directory(self, file_column_name: str = None, table_file_path: str = None,
                                        read_method_file: Callable = None, update_counter: int = 1000,
                                        append_file_content: bool = True,
                                        read_method_return_list: bool = False) -> list:
        r"""Utility function to collect single files in :obj:`file_directory` by names in CSV table file.

        Args:
            file_column_name (str): Name of the column in Table file that holds list of file names.
            table_file_path (str): Path to table file. Can be None. Default is None.
            read_method_file (Callable): Callable read-file method to return (processed) file content.
            update_counter (int): Loop counter to show progress. Default is 1000.
            append_file_content (bool): Whether to append or add return of :obj:`read_method_file`.
            read_method_return_list (bool): Whether :obj:`read_method_file` returns list of items or the item itself.

        Returns:
            list: File content loaded from single files.
        """
        self.read_in_table_file(table_file_path)
        if self.data_frame is None:
            raise FileNotFoundError("Can not find '.csv' table path '%s'." % table_file_path)

        if file_column_name is None:
            raise ValueError("Please specify column for '.csv' file which contains file names.")

        if file_column_name not in self.data_frame.columns:
            raise ValueError(
                "Can not find file names of column '%s' in '%s'" % (file_column_name, self.data_frame.columns))

        name_file_list = self.data_frame[file_column_name].values
        num_files = len(name_file_list)

        if not os.path.exists(self.file_directory_path):
            raise ValueError("No file directory found at '%s'." % self.file_directory_path)

        self.info("Read %s single files." % num_files)
        out_list = []
        for i, x in enumerate(name_file_list):
            # Only one file per path
            file_loaded = read_method_file(os.path.join(self.file_directory_path, x))
            if append_file_content:
                if read_method_return_list:
                    out_list.append(file_loaded[0])
                else:
                    out_list.append(file_loaded)
            else:
                if read_method_return_list:
                    out_list += file_loaded
                else:
                    out_list += [file_loaded]
            if i % update_counter == 0:
                self.info("... Read {0} file {1} from {2}".format(os.path.splitext(x)[1], i, num_files))

        return out_list

    def set_methods(self, method_list: List[dict]) -> None:
        r"""Apply a list of serialized class-methods on the dataset.

        This can extend the config-serialization scheme in :obj:`kgcnn.utils.serial`.

        .. code-block:: python

            for method_item in method_list:
                for method, kwargs in method_item.items():
                    if hasattr(self, method):
                        getattr(self, method)(**kwargs)

        Args:
            method_list (list): A list of dictionaries that specify class methods. The `dict` key denotes the method
                and the value must contain `kwargs` for the method

        Returns:
            None.
        """
        for method_item in method_list:
            for method, kwargs in method_item.items():
                if hasattr(self, method):
                    getattr(self, method)(**kwargs)
                else:
                    self.error("Class does not have method '%s'." % method)

    def get_split_indices(self, name: str = "kfold", return_as_train_test: bool = True,
                          shuffle: bool = True, seed: int = None):
        """Gather split ids from split graph property and return k-fold splits.

        Args:
            name (str): Name of property containing split assignment. Default is "kfold".
            return_as_train_test (bool): Whether to return the splits as train test indices. Default is True.
            shuffle (bool): Whether to shuffle splits. Default is True.
            seed (int): Random seed for shuffle. Default is None.

        Returns:
            list: List of splits.
        """
        split_indices = [[]]

        def check_and_extend_splits(to_split):
            if to_split - len(split_indices) + 1 > 0:
                for _ in range(to_split - len(split_indices) + 1):
                    split_indices.append([])

        graphs = self.obtain_property(name)
        for i, s in enumerate(graphs):
            if s is None:
                self.error("Split assignment on graph '%s' is not defined." % i)
                continue
            for x in s:
                check_and_extend_splits(x)
                split_indices[int(x)].append(i)

        split_indices = [np.array(x, dtype="int") for x in split_indices]

        if shuffle:
            np.random.seed(seed)
            for x in split_indices:
                np.random.shuffle(x)

        if not return_as_train_test:
            return split_indices

        train_test = []

        for i in range(len(split_indices)):
            train = np.concatenate([x for j, x in enumerate(split_indices) if j != i], axis=0)
            test = split_indices[i]
            train_test.append([train, test])

        return train_test

    def get_train_test_indices(self, train: str = "train", test: str = "test", valid: str = None,
                               split_index: Union[int, list] = 1):
        """Get train and test indices from graph list. The 'train' and 'test' properties must be set on the graph.
        They can also be a list of split assignment if more than one train-test split is required.

        Args:
            train (str): Name of graph property that has train split assignment. Defaults to 'train'.
            test (str): Name of graph property that has test split assignment. Defaults to 'test'.
            valid (str): Name of graph property that has validation assignment. Defaults to None.
            split_index (int, list): Split index to get indices for. Can also be list.

        Returns:
            list: list of train, test, validation split indices.
        """
        out_indices = []
        if not isinstance(split_index, (list, tuple)):
            split_index = [split_index]
        for s in [train, test, valid]:
            if s is None:
                out_indices.append(None)
                continue
            s_list = []
            split_prop = self.obtain_property(s)
            for j in split_index:
                split_list = []
                for i, x in enumerate(split_prop):
                    if x is not None:
                        if j in x:
                            split_list.append(i)
                s_list.append(split_list)
            if len(s_list) == 1:
                out_indices.append(s_list[0])
            else:
                out_indices.append(s_list[0])

        return out_indices


MemoryGeometricGraphDataset = MemoryGraphDataset
