hyper = {
    "Schnet": {
        "model": {
            "name": "Schnet",
            "inputs": [
                {"shape": [None], "name": "node_number", "dtype": "float32", "ragged": True},
                {"shape": [None, 3], "name": "node_coordinates", "dtype": "float32", "ragged": True},
                {"shape": [None, 2], "name": "range_indices", "dtype": "int64", "ragged": True}
            ],
            "input_embedding": {
                "node": {"input_dim": 95, "output_dim": 64}
            },
            "output_mlp": None,
            "output_embedding": "graph",
            "last_mlp": {"use_bias": [True, True, True], "units": [128, 64, 3],
                         "activation": ['kgcnn>shifted_softplus', 'kgcnn>shifted_softplus', 'linear']},
            "interaction_args": {
                "units": 128, "use_bias": True, "activation": "kgcnn>shifted_softplus", "cfconv_pool": "sum"
            },
            "node_pooling_args": {"pooling_method": "sum"},
            "depth": 4,
            "gauss_args": {"bins": 20, "distance": 4, "offset": 0.0, "sigma": 0.4}, "verbose": 1
        },
        "training": {
            "KFold": {"n_splits": 10, "random_state": None, "shuffle": True},
            "execute_folds": 1,
            "fit": {
                "batch_size": 32, "epochs": 800, "validation_freq": 10, "verbose": 2,
                "callbacks": [
                    {"class_name": "kgcnn>LinearLearningRateScheduler", "config": {
                        "learning_rate_start": 0.0005, "learning_rate_stop": 1e-05, "epo_min": 100, "epo": 800,
                        "verbose": 0}
                     }
                ]
            },
            "compile": {
                "optimizer": {"class_name": "Adam", "config": {"lr": 0.0005}},
                "loss": "mean_absolute_error"
            }
        },
        "data": {
            "set_range": {"max_distance": 4, "max_neighbours": 30},
            "data_points_to_use": 133885,
            "target_indices": [5, 6, 7]
        },
        "info": {
            "postfix": "",
            "postfix_file": "_homo_lumo_gap",
            "kgcnn_version": "1.2.0"
        }
    },
    "Megnet": {
        "model": {
            "name": "Megnet",
            "inputs": [
                {"shape": [None], "name": "node_number", "dtype": "float32", "ragged": True},
                {"shape": [None, 3], "name": "node_coordinates", "dtype": "float32", "ragged": True},
                {"shape": [None, 2], "name": "range_indices", "dtype": "int64", "ragged": True},
                {"shape": [2], "name": "graph_attributes", "dtype": "float32", "ragged": False}
            ],
            "input_embedding": {"node": {"input_dim": 10, "output_dim": 16},
                                "graph": {"input_dim": 100, "output_dim": 64}},
            "output_embedding": "graph",
            "output_mlp": {"use_bias": [True, True, True], "units": [32, 16, 3],
                           "activation": ["kgcnn>softplus2", "kgcnn>softplus2", "linear"]},
            "gauss_args": {"bins": 20, "distance": 4, "offset": 0.0, "sigma": 0.4},
            "meg_block_args": {"node_embed": [64, 32, 32], "edge_embed": [64, 32, 32],
                               "env_embed": [64, 32, 32], "activation": "kgcnn>softplus2"},
            "set2set_args": {"channels": 16, "T": 3, "pooling_method": "sum", "init_qstar": "0"},
            "node_ff_args": {"units": [64, 32], "activation": "kgcnn>softplus2"},
            "edge_ff_args": {"units": [64, 32], "activation": "kgcnn>softplus2"},
            "state_ff_args": {"units": [64, 32], "activation": "kgcnn>softplus2",
                              "input_tensor_type": "tensor"},
            "nblocks": 3, "has_ff": True, "dropout": None, "use_set2set": True,
            "verbose": 1
        },
        "training": {
            "KFold": {"n_splits": 10, "random_state": None, "shuffle": True},
            "execute_folds": 1,
            "fit": {
                "batch_size": 32, "epochs": 800, "validation_freq": 10, "verbose": 2,
                "callbacks": [
                    {"class_name": "kgcnn>LinearLearningRateScheduler", "config": {
                        "learning_rate_start": 0.0005, "learning_rate_stop": 1e-05, "epo_min": 100, "epo": 800,
                        "verbose": 0
                    }
                     }
                ]
            },
            "compile": {
                "optimizer": {"class_name": "Adam", "config": {"lr": 0.0005}},
                "loss": "mean_absolute_error"
            }
        },
        "data": {
            "set_range": {"max_distance": 4, "max_neighbours": 30},
            "data_points_to_use": 133885,
            "target_indices": [5, 6, 7]
        },
        "info": {
            "postfix": "",
            "postfix_file": "_homo_lumo_gap",
            "kgcnn_version": "1.1.0"
        }
    },
    "NMPN": {
        "model": {
            "name": "NMPN",
            "inputs": [{"shape": [None], "name": "node_attributes", "dtype": "float32", "ragged": True},
                       {"shape": [None, 1], "name": "edge_attributes", "dtype": "float32", "ragged": True},
                       {"shape": [None, 2], "name": "edge_indices", "dtype": "int64", "ragged": True}],
            "input_embedding": {"node": {"input_dim": 95, "output_dim": 64},
                                "edge": {"input_dim": 5, "output_dim": 64}},
            "output_embedding": "graph",
            "output_mlp": {"use_bias": [True, True, False], "units": [25, 25, 3],
                           "activation": ["selu", "selu", "linear"]},
            "set2set_args": {"channels": 32, "T": 3, "pooling_method": "sum", "init_qstar": "0"},
            "pooling_args": {"pooling_method": "segment_mean"},
            "edge_dense": {"use_bias": True, "activation": "selu"},
            "use_set2set": True,
            "depth": 3,
            "node_dim": 128,
            "verbose": 1
        },
        "training": {
            "KFold": {"n_splits": 10, "random_state": None, "shuffle": True},
            "execute_folds": 1,
            "fit": {
                "batch_size": 32, "epochs": 800, "validation_freq": 10, "verbose": 2,
                "callbacks": [
                    {"class_name": "kgcnn>LinearLearningRateScheduler", "config": {
                        "learning_rate_start": 0.0005, "learning_rate_stop": 1e-05, "epo_min": 100, "epo": 800,
                        "verbose": 0
                    }
                     }
                ]
            },
            "compile": {"optimizer": {"class_name": "Adam", "config": {"lr": 0.0005}},
                        "loss": "mean_absolute_error"
                        }
        },
        "data": {
            "set_range": {"max_distance": 4, "max_neighbours": 30},
            "data_points_to_use": 133885,
            "target_indices": [5, 6, 7]
        },
        "info": {
            "postfix": "",
            "postfix_file": "_homo_lumo_gap",
            "kgcnn_version": "1.1.0"
        }
    },
    "PAiNN": {
        "model": {
            "name": "PAiNN",
            "inputs": [
                {"shape": [None], "name": "node_number", "dtype": "float32", "ragged": True},
                {"shape": [None, 3], "name": "node_coordinates", "dtype": "float32", "ragged": True},
                {"shape": [None, 2], "name": "range_indices", "dtype": "int64", "ragged": True}
            ],
            "input_embedding": {"node": {"input_dim": 95, "output_dim": 128}},
            "output_embedding": "graph",
            "output_mlp": {"use_bias": [True, True], "units": [128, 3], "activation": ["swish", "linear"]},
            "bessel_basis": {"num_radial": 20, "cutoff": 5.0, "envelope_exponent": 5},
            "pooling_args": {"pooling_method": "sum"}, "conv_args": {"units": 128, "cutoff": None},
            "update_args": {"units": 128}, "depth": 3, "verbose": 1
        },
        "training": {
            "KFold": {"n_splits": 10, "random_state": None, "shuffle": True},
            "execute_folds": 1,
            "fit": {
                "batch_size": 32, "epochs": 872, "validation_freq": 10, "verbose": 2, "callbacks": []
            },
            "compile": {
                "optimizer": {
                    "class_name": "Addons>MovingAverage", "config": {
                        "optimizer": {
                            "class_name": "Adam", "config": {
                                "learning_rate": {
                                    "class_name": "kgcnn>LinearWarmupExponentialDecay", "config": {
                                        "learning_rate": 0.001, "warmup_steps": 3000.0, "decay_steps": 4000000.0,
                                        "decay_rate": 0.01
                                    }
                                }, "amsgrad": True
                            }
                        },
                        "average_decay": 0.999
                    }
                },
                "loss": "mean_absolute_error"
            }
        },
        "data": {
            "set_range": {"max_distance": 5, "max_neighbours": 10000},
            "data_points_to_use": 133885,
            "target_indices": [5, 6, 7]
        },
        "info": {
            "postfix": "",
            "postfix_file": "_homo_lumo_gap",
            "kgcnn_version": "1.1.0"
        }
    },
    "DimeNetPP": {
        "model": {
            "name": "DimeNetPP",
            "inputs": [{"shape": [None], "name": "node_number", "dtype": "float32", "ragged": True},
                       {"shape": [None, 3], "name": "node_coordinates", "dtype": "float32", "ragged": True},
                       {"shape": [None, 2], "name": "range_indices", "dtype": "int64", "ragged": True},
                       {"shape": [None, 2], "name": "angle_indices", "dtype": "int64", "ragged": True}],
            "input_embedding": {"node": {"input_dim": 95, "output_dim": 128,
                                         "embeddings_initializer": {"class_name": "RandomUniform",
                                                                    "config": {"minval": -1.7320508075688772,
                                                                               "maxval": 1.7320508075688772}}}},
            "output_embedding": "graph",
            "output_mlp": None,
            "emb_size": 128, "out_emb_size": 256, "int_emb_size": 64, "basis_emb_size": 8,
            "num_blocks": 4, "num_spherical": 7, "num_radial": 6,
            "cutoff": 5.0, "envelope_exponent": 5,
            "num_before_skip": 1, "num_after_skip": 2, "num_dense_output": 3,
            "num_targets": 3, "extensive": False, "output_init": "zeros",
            "activation": "swish", "verbose": 1
        },
        "training": {
            "KFold": {"n_splits": 10, "random_state": None, "shuffle": True},
            "execute_folds": 1,
            "fit": {
                "batch_size": 10, "epochs": 872, "validation_freq": 10, "verbose": 2, "callbacks": []
            },
            "compile": {
                "optimizer": {
                    "class_name": "Addons>MovingAverage", "config": {
                        "optimizer": {
                            "class_name": "Adam", "config": {
                                "learning_rate": {
                                    "class_name": "kgcnn>LinearWarmupExponentialDecay", "config": {
                                        "learning_rate": 0.001, "warmup_steps": 3000.0, "decay_steps": 4000000.0,
                                        "decay_rate": 0.01
                                    }
                                }, "amsgrad": True
                            }
                        },
                        "average_decay": 0.999
                    }
                },
                "loss": "mean_absolute_error"
            }
        },
        "data": {
            "set_range": {"max_distance": 5, "max_neighbours": 10000},
            "angle": {},
            "data_points_to_use": 133885,
            "target_indices": [5, 6, 7]
        },
        "info": {
            "postfix": "",
            "postfix_file": "_homo_lumo_gap",
            "kgcnn_version": "1.1.0"
        }
    }
}
