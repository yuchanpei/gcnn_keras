![GitHub release (latest by date)](https://img.shields.io/github/v/release/aimat-lab/gcnn_keras)
[![Documentation Status](https://readthedocs.org/projects/kgcnn/badge/?version=latest)](https://kgcnn.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/kgcnn.svg)](https://badge.fury.io/py/kgcnn)
![PyPI - Downloads](https://img.shields.io/pypi/dm/kgcnn)
[![kgcnn_unit_tests](https://github.com/aimat-lab/gcnn_keras/actions/workflows/unittests.yml/badge.svg)](https://github.com/aimat-lab/gcnn_keras/actions/workflows/unittests.yml)
[![DOI](https://img.shields.io/badge/DOI-10.1016%2Fj.simpa.2021.100095%20-blue)](https://doi.org/10.1016/j.simpa.2021.100095)
![GitHub](https://img.shields.io/github/license/aimat-lab/gcnn_keras)
![GitHub issues](https://img.shields.io/github/issues/aimat-lab/gcnn_keras)
![Maintenance](https://img.shields.io/maintenance/yes/2021)

# Keras Graph Convolution Neural Networks
<p align="left">
  <img src="https://github.com/aimat-lab/gcnn_keras/blob/master/docs/source/_static/icon.svg" height="80"/>
</p>

A set of layers for graph convolutions in TensorFlow Keras that use RaggedTensors.

* [General](#general)
* [Requirements](#requirements)
* [Installation](#installation)
* [Documentation](#documentation)
* [Implementation details](#implementation-details)
* [Literature](#literature)
* [Datasets](#datasets)
* [Examples](#examples)
* [Issues](#issues)
* [Citing](#citing)
* [References](#references)
 

<a name="general"></a>
# General

The package in [kgcnn](kgcnn) contains several layer classes to build up graph convolution models. 
Some models are given as an example.
A [documentation](https://kgcnn.readthedocs.io/en/latest/index.html) is generated in [docs](docs).
This repo is still under construction.
Any comments, suggestions or help are very welcome!

<a name="requirements"></a>
# Requirements

For kgcnn, usually the latest version of tensorflow is required, but is listed as extra requirements in the `setup.py` for simplicity. 
Additional python packages are placed in the `setup.py` requirements and are installed automatically. 
Packages which must be installed manually for full functionality:

* tensorflow>=2.4.1
* rdkit>=2020.03.4
* openbabel>=3.0.1
* pymatgen>=??.??.??

<a name="installation"></a>
# Installation

Clone repository https://github.com/aimat-lab/gcnn_keras and install with editable mode:

```bash
pip install -e ./gcnn_keras
```
or latest release via Python Package Index.
```bash
pip install kgcnn
```
<a name="documentation"></a>
# Documentation

Auto-documentation is generated at https://kgcnn.readthedocs.io/en/latest/index.html .

<a name="implementation-details"></a>
# Implementation details

### Representation
The most frequent usage for graph convolutions is either node or graph classification. As for their size, either a single large graph, e.g. citation network or small (batched) graphs like molecules have to be considered. 
Graphs can be represented by an index list of connections plus feature information. Typical quantities in tensor format to describe a graph are listed below.

* `nodes`: Node-list of shape `(batch, [N], F)` where `N` is the number of nodes and `F` is the node feature dimension.
* `edges`: Edge-list of shape `(batch, [M], F)` where `M` is the number of edges and `F` is the edge feature dimension.
* `indices`: Connection-list of shape `(batch, [M], 2)` where `M` is the number of edges. The indices denote a connection of incoming or receiving node `i` and outgoing or sending node `j` as `(i, j)`.
* `state`: Graph state information of shape `(batch, F)` where `F` denotes the feature dimension.
 
A major issue for graphs is their flexible size and shape, when using mini-batches. Here, for a graph implementation in the spirit of keras, the batch dimension should be kept also in between layers. This is realized by using `RaggedTensor`s.


### Input

Here, for ragged tensors, the nodelist of shape `(batch, None, F)` and edgelist of shape `(batch, None, F')` have one ragged dimension `(None, )`.
The graph structure is represented by an index-list of shape `(batch, None, 2)` with index of incoming or receiving node `i` and outgoing or sending node `j` as `(i, j)`. 
The first index of incoming node `i` is usually sorted for faster pooling operations, but can also be unsorted. 
Furthermore, the graph is directed, so an additional edge with `(j, i)` is required for undirected graphs. 
A ragged constant can be directly obtained from a list of numpy arrays: `tf.ragged.constant(indices, ragged_rank=1, inner_shape=(2, ))` which yields shape `(batch, None, 2)`.

### Model

Models can be set up in a functional way. Example message passing from fundamental operations:

```python
import tensorflow.keras as ks
from kgcnn.layers.gather import GatherNodes
from kgcnn.layers.modules import DenseEmbedding, LazyConcatenate  # ragged support
from kgcnn.layers.pooling import PoolingLocalMessages, PoolingNodes

n = ks.layers.Input(shape=(None, 3), name='node_input', dtype="float32", ragged=True)
ei = ks.layers.Input(shape=(None, 2), name='edge_index_input', dtype="int64", ragged=True)

n_in_out = GatherNodes()([n, ei])
node_messages = DenseEmbedding(10, activation='relu')(n_in_out)
node_updates = PoolingLocalMessages()([n, node_messages, ei])
n_node_updates = LazyConcatenate(axis=-1)([n, node_updates])
n_embedd = DenseEmbedding(1)(n_node_updates)
g_embedd = PoolingNodes()(n_embedd)

message_passing = ks.models.Model(inputs=[n, ei], outputs=g_embedd)
```

or via sub-classing of the message passing base layer. Where only `message_function` and `update_nodes` must be implemented:

```python
from kgcnn.layers.conv.message import MessagePassingBase
from kgcnn.layers.modules import DenseEmbedding, LazyAdd

class MyMessageNN(MessagePassingBase):
  def __init__(self, units, **kwargs):
    super(MyMessageNN, self).__init__(**kwargs)
    self.dense = DenseEmbedding(units)
    self.add = LazyAdd(axis=-1)
  
  def message_function(self, inputs, **kwargs):
    n_in, n_out, edges = inputs
    return self.dense(n_out)
  
  def update_nodes(self, inputs, **kwargs):
    nodes, nodes_update = inputs
    return self.add([nodes, nodes_update])
```

<a name="literature"></a>
# Literature
A version of the following models are implemented in [literature](kgcnn/literature):
* **[GCN](kgcnn/literature/GCN.py)**: [Semi-Supervised Classification with Graph Convolutional Networks](https://arxiv.org/abs/1609.02907) by Kipf et al. (2016)
* **[INorp](kgcnn/literature/INorp.py)**: [Interaction Networks for Learning about Objects,Relations and Physics](https://arxiv.org/abs/1612.00222) by Battaglia et al. (2016)
* **[Megnet](kgcnn/literature/Megnet.py)**: [Graph Networks as a Universal Machine Learning Framework for Molecules and Crystals](https://doi.org/10.1021/acs.chemmater.9b01294) by Chen et al. (2019)
* **[NMPN](kgcnn/literature/NMPN.py)**: [Neural Message Passing for Quantum Chemistry](http://arxiv.org/abs/1704.01212) by Gilmer et al. (2017)
* **[Schnet](kgcnn/literature/Schnet.py)**: [SchNet – A deep learning architecture for molecules and materials ](https://aip.scitation.org/doi/10.1063/1.5019779) by Schütt et al. (2017)
* **[Unet](kgcnn/literature/Unet.py)**: [Graph U-Nets](http://proceedings.mlr.press/v97/gao19a/gao19a.pdf) by H. Gao and S. Ji (2019)
* **[GNNExplainer](kgcnn/literature/GNNExplain.py)**: [GNNExplainer: Generating Explanations for Graph Neural Networks](https://arxiv.org/abs/1903.03894) by Ying et al. (2019)
* **[GraphSAGE](kgcnn/literature/GraphSAGE.py)**: [Inductive Representation Learning on Large Graphs](http://arxiv.org/abs/1706.02216) by Hamilton et al. (2017)
* **[GAT](kgcnn/literature/GAT.py)**: [Graph Attention Networks](https://arxiv.org/abs/1710.10903) by Veličković et al. (2018)
* **[GATv2](kgcnn/literature/GATv2.py)**: [How Attentive are Graph Attention Networks?](https://arxiv.org/abs/2105.14491) by Brody et al. (2021)
* **[DimeNetPP](kgcnn/literature/DimeNetPP.py)**: [Fast and Uncertainty-Aware Directional Message Passing for Non-Equilibrium Molecules](https://arxiv.org/abs/2011.14115) by Klicpera et al. (2020)
* **[AttentiveFP](kgcnn/literature/AttentiveFP.py)**: [Pushing the Boundaries of Molecular Representation for Drug Discovery with the Graph Attention Mechanism](https://pubs.acs.org/doi/10.1021/acs.jmedchem.9b00959) by Xiong et al. (2019)
* **[GIN](kgcnn/literature/GIN.py)**: [How Powerful are Graph Neural Networks?](https://arxiv.org/abs/1810.00826) by Xu et al. (2019)
* **[PAiNN](kgcnn/literature/PAiNN.py)**: [Equivariant message passing for the prediction of tensorial properties and molecular spectra](https://arxiv.org/pdf/2102.03150.pdf) by Schütt et al. (2020)
* **[DMPNN](kgcnn/literature/DMPNN.py)**: [Analyzing Learned Molecular Representations for Property Prediction](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.9b00237) by Yang et al. (2019)

<a name="datasets"></a>
# Datasets

The base class is `MemoryGraphDataset` which holds a lists of graph properties in tensor-like numpy arrays.
Each property that starts with `node_`, `edge_`, `graph_` holds a list with length of the dataset that fit into memory. 
Furthermore, file information on disk can be provided in the constructor, that points to a `data_directory` for the dataset.

```bash
├── data_directory
    ├── file_directory
    │   ├── *.*
    │   └── ... 
    ├── file_name
    └── dataset_name.pickle
```
Create and store a general dataset via:

```python
from kgcnn.data.base import MemoryGraphDataset
import numpy as np
dataset = MemoryGraphDataset(data_directory="ExampleDir", dataset_name="Example", length=1)
dataset.edge_indices = [np.array([[1, 0], [0, 1]])]
dataset.edge_labels = [np.array([[0], [1]])]
dataset.save()
dataset.load()
```

The subclasses `QMDataset`, `MoleculeNetDataset` and `GraphTUDataset` further have functions required for the specific dataset to convert and load files such as ".txt", ".sdf", ".xyz" etc. via `prepare_data()` and `read_in_memory()`.

```python
from kgcnn.data.qm import QMDataset
dataset = QMDataset(data_directory="ExampleDir", dataset_name="methane", 
                    file_name="geom.xyz", file_directory=None)
dataset.prepare_data()  # Also make .sdf
dataset.read_in_memory()
```

In [data.datasets](kgcnn/data/datasets) there are graph learning datasets as subclasses which are being downloaded from e.g. 
TUDatasets or MoleculeNet and directly processed and loaded. They are stored at `~/.kgcnn/datasets`.

```python
from kgcnn.data.datasets.MUTAGDataset import MUTAGDataset
dataset = MUTAGDataset()
print(dataset.edge_indices[0])
```

<a name="examples"></a>
# Examples

A set of example training can be found in [training](training).

# Issues

Some known issues to be aware of, if using and making new models or layers with `kgcnn`.
* RaggedTensor can not yet be used as a keras model output (https://github.com/tensorflow/tensorflow/issues/42320), which means only padded tensors can be used for batched node embedding tasks.
* Using `RaggedTensor`'s for arbitrary ragged rank apart from `kgcnn.layers.modules` can cause significant performance decrease. This is due to shape check during add, multiply or concatenate (we think). 
  We therefore use lazy add and concat in the `kgcnn.layers.modules` layers or directly operate on the value tensor for possible rank. 
* With tensorflow version <=2.5 there is a problem with numpy version >=1.20 also affect `kgcnn` (https://github.com/tensorflow/tensorflow/issues/47691) 

<a name="citing"></a>
# Citing

If you want to cite this repo, refer to our paper:

```
@article{REISER2021100095,
title = {Graph neural networks in TensorFlow-Keras with RaggedTensor representation (kgcnn)},
journal = {Software Impacts},
pages = {100095},
year = {2021},
issn = {2665-9638},
doi = {https://doi.org/10.1016/j.simpa.2021.100095},
url = {https://www.sciencedirect.com/science/article/pii/S266596382100035X},
author = {Patrick Reiser and Andre Eberhard and Pascal Friederich}
}
```

<a name="references"></a>
# References

- https://www.tensorflow.org/api_docs/python/tf/RaggedTensor
