import os
import numpy as np
import pandas as pd
from typing import Union, Callable, List, Dict
from kgcnn.mol.base import MolGraphInterface
from kgcnn.scaler.mol import QMGraphLabelScaler
from sklearn.preprocessing import StandardScaler
from kgcnn.mol.serial import deserialize_encoder
from kgcnn.data.base import MemoryGraphDataset
from kgcnn.mol.io import parse_list_to_xyz_str, read_xyz_file, \
    write_mol_block_list_to_sdf, read_mol_list_from_sdf_file, write_list_to_xyz_file
from kgcnn.mol.methods import global_proton_dict, inverse_global_proton_dict
from kgcnn.mol.convert import MolConverter
from kgcnn.data.moleculenet import map_molecule_callbacks

try:
    from kgcnn.mol.graph_babel import MolecularGraphOpenBabel
except ModuleNotFoundError:
    MolecularGraphOpenBabel = None


class QMDataset(MemoryGraphDataset):
    r"""This is a base class for QM (quantum mechanical) datasets.

    It generates graph properties from a xyz-file, which stores atomic coordinates.
    Additionally, loading multiple single xyz-files into one file is supported. The file names and labels are given
    by a CSV or table file. The table file must have one line of header with column names!

    .. code-block:: type

        ├── data_directory
            ├── file_directory
            │   ├── *.xyz
            │   ├── *.xyz
            │   └── ...
            ├── file_name.csv
            ├── file_name.xyz
            ├── file_name.sdf
            └── dataset_name.kgcnn.pickle

    It should be possible to generate approximate chemical bonding information via `openbabel`, if this
    additional package is installed. The class inherits from :obj:`MemoryGraphDataset` and :obj:`MolGraphCallbacks`.
    If `openbabel` is not installed minimal loading of labels and coordinates should be supported.

    For additional attributes, the :obj:`set_attributes` enables further features that require RDkit or Openbabel
    to be installed.

    """

    _global_proton_dict = global_proton_dict
    _inverse_global_proton_dict = inverse_global_proton_dict
    _default_loop_update_info = 5000
    _mol_graph_interface = MolecularGraphOpenBabel

    def __init__(self, data_directory: str = None, dataset_name: str = None, file_name: str = None,
                 verbose: int = 10, file_directory: str = None):
        r"""Default initialization. File information on the location of the dataset on disk should be provided here.

        Args:
            data_directory (str): Full path to directory of the dataset. Default is None.
            file_name (str): Filename for reading into memory. This must be the base-name of a '.xyz' file.
                Or additionally the name of a '.csv' formatted file that has a list of file names.
                Files are expected to be in :obj:`file_directory`. Default is None.
            file_directory (str): Name or relative path from :obj:`data_directory` to a directory containing sorted
                '.xyz' files. Only used if :obj:`file_name` is None. Default is None.
            dataset_name (str): Name of the dataset. Important for naming and saving files. Default is None.
            verbose (int): Logging level. Default is 10.
        """
        MemoryGraphDataset.__init__(self, data_directory=data_directory, dataset_name=dataset_name,
                                    file_name=file_name, verbose=verbose,
                                    file_directory=file_directory)
        self.label_units = None
        self.label_names = None

    @property
    def file_path_mol(self):
        """Try to determine a file name for the mol information to store."""
        return os.path.splitext(self.file_path)[0] + ".sdf"

    @property
    def file_path_xyz(self):
        """Try to determine a file name for the mol information to store."""
        return os.path.splitext(self.file_path)[0] + ".xyz"

    def get_geom_from_xyz_file(self, file_path: str) -> list:
        """Get a list of xyz items from file.

        Args:
            file_path (str): File path of XYZ file. Default None uses :obj:`file_path_xyz`.

        Returns:
            list: List of xyz lists.
        """
        if file_path is None:
            file_path = self.file_path_xyz
        return read_xyz_file(file_path)

    def get_mol_blocks_from_sdf_file(self, file_path: str = None) -> list:
        """Get a list of mol-blocks from file.

        Args:
            file_path (str): File path of SDF file. Default None uses :obj:`file_path_mol`.

        Returns:
            list: List of mol-strings.
        """
        if file_path is None:
            file_path = self.file_path_mol
        if not os.path.exists(file_path):
            raise FileNotFoundError("Can not load SDF for dataset %s" % self.dataset_name)
        # Loading the molecules and the csv data
        mol_list = read_mol_list_from_sdf_file(file_path)
        if mol_list is None:
            self.warning("Failed to load bond information from SDF file.")
        return mol_list

    def prepare_data(self, overwrite: bool = False, file_column_name: str = None, make_sdf: bool = True):
        r"""Pre-computation of molecular structure information in a sdf-file from a xyz-file or a folder of xyz-files.

        If there is no single xyz-file, it will be created with the information of a csv-file with the same name.

        Args:
            overwrite (bool): Overwrite existing database SDF file. Default is False.
            file_column_name (str): Name of the column in csv file with list of xyz-files located in file_directory
            make_sdf (bool): Whether to try to make a sdf file from xyz information via OpenBabel.

        Returns:
            self
        """
        if os.path.exists(self.file_path_mol) and not overwrite:
            self.info("Found SDF file '%s' of pre-computed structures." % self.file_path_mol)
            return self

        # Try collect single xyz files in directory
        xyz_list = None
        if not os.path.exists(self.file_path_xyz):
            xyz_list = self.collect_files_in_file_directory(
                file_column_name=file_column_name, table_file_path=None,
                read_method_file=self.get_geom_from_xyz_file, update_counter=self._default_loop_update_info,
                append_file_content=True, read_method_return_list=True
            )
            write_list_to_xyz_file(self.file_path_xyz, xyz_list)

        # Additionally, try to make SDF file. Requires openbabel.
        if make_sdf:
            self.info("Converting xyz to mol information.")
            converter = MolConverter()
            converter.xyz_to_mol(self.file_path_xyz, self.file_path_mol)
        return self

    def read_in_memory_xyz(self, file_path: str = None):
        """Read XYZ-file with geometric information into memory.

        Args:
            file_path (str): Filepath to xyz file.

        Returns:
            self
        """
        xyz_list = self.get_geom_from_xyz_file(file_path)
        symbol = [np.array(x[0]) for x in xyz_list]
        coord = [np.array(x[1], dtype="float")[:, :3] for x in xyz_list]
        nodes = [np.array([self._global_proton_dict[x] for x in y[0]], dtype="int") for y in xyz_list]
        for key, value in {"node_coordinates": coord, "node_symbol": symbol, "node_number": nodes}.items():
            self.assign_property(key, value)
        return self

    def set_attributes(self,
                       label_column_name: Union[str, list] = None,
                       nodes: list = None,
                       edges: list = None,
                       graph: list = None,
                       encoder_nodes: dict = None,
                       encoder_edges: dict = None,
                       encoder_graph: dict = None,
                       add_hydrogen: bool = True,
                       make_directed: bool = False,
                       additional_callbacks: Dict[str, Callable[[MolGraphInterface, dict], None]] = None,
                       custom_transform: Callable[[MolGraphInterface], MolGraphInterface] = None
                       ):
        """Read SDF-file with chemical structure information into memory.

        Args:
            label_column_name (str, list): Name of labels for columns in CSV file.
            nodes (list): A list of node attributes as string. In place of names also functions can be added.
            edges (list): A list of edge attributes as string. In place of names also functions can be added.
            graph (list): A list of graph attributes as string. In place of names also functions can be added.
            encoder_nodes (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_edges (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_graph (dict): A dictionary of callable encoder where the key matches the attribute.
            add_hydrogen (bool): Whether to keep hydrogen after reading the mol-information. Default is False.
            make_directed (bool): Whether to have directed or undirected bonds. Default is False.
            additional_callbacks (dict): A dictionary whose keys are string attribute names which the elements of the
                dataset are supposed to have and the elements are callback function objects which implement how those
                attributes are derived from the :obj:`MolecularGraphRDKit` of the molecule in question or the
                row of the CSV file.
            custom_transform (Callable): Custom transformation function to modify the generated
                :obj:`MolecularGraphRDKit` before callbacks are carried out. The function must take a single
                :obj:`MolecularGraphRDKit` instance as argument and return a (new) :obj:`MolecularGraphRDKit` instance.

        Returns:
            self
        """
        additional_callbacks = additional_callbacks if additional_callbacks is not None else {}

        # Deserializing encoders.
        for encoder in [encoder_nodes, encoder_edges, encoder_graph]:
            if encoder is not None:
                for key, value in encoder.items():
                    encoder[key] = deserialize_encoder(value)

        callbacks = {
            "node_symbol": lambda mg, ds: mg.node_symbol,
            "node_number": lambda mg, ds: mg.node_number,
            "node_coordinates": lambda mg, ds: mg.node_coordinates,
            "edge_indices": lambda mg, ds: mg.edge_number[0],
            "edge_number": lambda mg, ds: np.array(mg.edge_number[1], dtype='int'),
            **additional_callbacks
        }
        # Label callback.
        if label_column_name:
            callbacks.update({'graph_labels': lambda mg, ds: ds[label_column_name]})
        # Attributes callback.
        for attrib, name, encoder in zip([nodes, edges, graph],
                                         ["node_attributes", "edge_attributes", "graph_attributes"],
                                         [encoder_nodes, encoder_edges, encoder_graph]):
            if attrib:
                callbacks.update({name: lambda mg, ds: np.array(getattr(mg, name)(attrib, encoder), dtype='float32')})

        value_list = map_molecule_callbacks(
            self.get_mol_blocks_from_sdf_file(),
            self.read_in_table_file().data_frame,
            callbacks=callbacks,
            add_hydrogen=add_hydrogen,
            custom_transform=custom_transform,
            make_directed=make_directed,
            mol_interface_class=MolecularGraphOpenBabel,
            logger=self.logger,
            loop_update_info=self._default_loop_update_info
        )

        for name, values in value_list.items():
            self.assign_property(name, values)

        return self

    def read_in_memory(self,
                       label_column_name: Union[str, list] = None,
                       nodes: list = None,
                       edges: list = None,
                       graph: list = None,
                       encoder_nodes: dict = None,
                       encoder_edges: dict = None,
                       encoder_graph: dict = None,
                       add_hydrogen: bool = True,
                       make_directed: bool = False,
                       additional_callbacks: Dict[str, Callable[[MolGraphInterface, dict], None]] = None,
                       custom_transform: Callable[[MolGraphInterface], MolGraphInterface] = None):
        """Read geometric information into memory.

        Graph labels require a column specified by :obj:`label_column_name`.

        Args:
            label_column_name (str, list): Name of labels for columns in CSV file.
            nodes (list): A list of node attributes as string. In place of names also functions can be added.
            edges (list): A list of edge attributes as string. In place of names also functions can be added.
            graph (list): A list of graph attributes as string. In place of names also functions can be added.
            encoder_nodes (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_edges (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_graph (dict): A dictionary of callable encoder where the key matches the attribute.
            add_hydrogen (bool): Whether to keep hydrogen after reading the mol-information. Default is False.
            make_directed (bool): Whether to have directed or undirected bonds. Default is False.
            additional_callbacks (dict): A dictionary whose keys are string attribute names which the elements of the
                dataset are supposed to have and the elements are callback function objects which implement how those
                attributes are derived from the :obj:`MolecularGraphRDKit` of the molecule in question or the
                row of the CSV file.
            custom_transform (Callable): Custom transformation function to modify the generated
                :obj:`MolecularGraphRDKit` before callbacks are carried out. The function must take a single
                :obj:`MolecularGraphRDKit` instance as argument and return a (new) :obj:`MolecularGraphRDKit` instance.

        Returns:
            self
        """
        if os.path.exists(self.file_path_mol) and self._mol_graph_interface is not None:
            self.info("Reading structures from SDF file.")
            self.set_attributes(
                label_column_name=label_column_name, nodes=nodes, edges=edges, graph=graph, encoder_nodes=encoder_nodes,
                encoder_edges=encoder_edges, encoder_graph=encoder_graph, add_hydrogen=add_hydrogen,
                make_directed=make_directed, additional_callbacks=additional_callbacks,
                custom_transform=custom_transform
            )
        else:
            # Try to read labels and xyz-file without mol-interface.
            self.warning("Failed to load structures SDF file. Reading geometries from XYZ file instead. Please check.")
            self.read_in_table_file()
            if self.data_frame is not None and label_column_name is not None:
                labels = self.data_frame[label_column_name]
                self.assign_property("graph_labels", [np.array(x) for _, x in labels.iterrows()])
            self.read_in_memory_xyz()
        return self
