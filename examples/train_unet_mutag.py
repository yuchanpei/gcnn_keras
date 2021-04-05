import time

# mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

from kgcnn.data.mutagen.mutag import mutag_graph
from kgcnn.literature.Unet import make_unet
from kgcnn.utils.adj import add_self_loops_to_indexlist
from kgcnn.utils.data import ragged_tensor_from_nested_numpy
from kgcnn.utils.learning import lr_lin_reduction

# Download and prepare dataset
labels, nodes, edge_indices, edges = mutag_graph()
labels[labels < 0] = 0
labels = np.expand_dims(labels, axis=-1)
graph_state = np.array([len(x) for x in nodes])
edge_indices = [add_self_loops_to_indexlist(x) for x in edge_indices]
edges = [np.ones_like(x, dtype=np.float)[:, 0:1] for x in edge_indices]

# Train Test split
labels_train, labels_test, nodes_train, nodes_test, edges_train, edges_test, edge_indices_train, edge_indices_test, graph_state_train, graph_state_test = train_test_split(
    labels, nodes, edges, edge_indices, graph_state, test_size=0.10, random_state=42)
del labels, nodes, edges, edge_indices, graph_state  # Free memory after split, if possible

# Convert to tf.RaggedTensor or tf.tensor
# A copy of the data is generated by ragged_tensor_from_nested_numpy()
nodes_train, edges_train, edge_indices_train, graph_state_train = ragged_tensor_from_nested_numpy(
    nodes_train), ragged_tensor_from_nested_numpy(edges_train), ragged_tensor_from_nested_numpy(
    edge_indices_train), tf.constant(graph_state_train)

nodes_test, edges_test, edge_indices_test, graph_state_test = ragged_tensor_from_nested_numpy(
    nodes_test), ragged_tensor_from_nested_numpy(edges_test), ragged_tensor_from_nested_numpy(
    edge_indices_test), tf.constant(graph_state_test)

# Define input and output data
xtrain = nodes_train, edges_train, edge_indices_train, graph_state_train
xtest = nodes_test, edges_test, edge_indices_test, graph_state_test
ytrain = labels_train
ytest = labels_test

model = make_unet(
    input_node_shape=[None],
    input_edge_shape=[None, 1],
    input_embedd={"input_node_vocab": 60,
                  "input_node_embedd": 128},
    # Output
    output_embedd={"output_mode": 'graph', "output_type": 'padded'},
    output_mlp={"use_bias": [True, False], "units": [25, 1],
                "activation": ['relu', 'sigmoid'],
                },
    # Model specific
    hidden_dim=128,
    depth=4,
    k=0.3,
    score_initializer='ones',
    use_bias=True,
    activation='relu',
    is_sorted=False,
    has_unconnected=True,
    use_reconnect=True
)

# Define learning rate
learning_rate_start = 1e-4
learning_rate_stop = 1e-5
epo = 500
epomin = 400
epostep = 2

# Compile model with optimizer
optimizer = tf.keras.optimizers.Adam(lr=learning_rate_start)
cbks = tf.keras.callbacks.LearningRateScheduler(lr_lin_reduction(learning_rate_start, learning_rate_stop, epomin, epo))
model.compile(loss='binary_crossentropy',
              optimizer=optimizer,
              metrics=['accuracy'])
print(model.summary())

start = time.process_time()
hist = model.fit(xtrain, ytrain,
                 epochs=epo,
                 batch_size=32,
                 callbacks=[cbks],
                 validation_freq=epostep,
                 validation_data=(xtest, ytest),
                 verbose=2
                 )
stop = time.process_time()
print("Print Time for taining: ", stop - start)

trainlossall = np.array(hist.history['accuracy'])
testlossall = np.array(hist.history['val_accuracy'])

mae_valid = testlossall[-1]

# Plot loss vs epochs
plt.figure()
plt.plot(np.arange(trainlossall.shape[0]), trainlossall, label='Training ACC', c='blue')
plt.plot(np.arange(epostep, epo + epostep, epostep), testlossall, label='Test ACC', c='red')
plt.scatter([trainlossall.shape[0]], [mae_valid], label="{0:0.4f} ".format(mae_valid), c='red')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('Interaction Network Loss')
plt.legend(loc='upper right', fontsize='x-large')
plt.savefig('unet_loss.png')
plt.show()
