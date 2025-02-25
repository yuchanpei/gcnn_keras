import numpy as np
import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package='kgcnn', name='LinearWarmupExponentialDecay')
class LinearWarmupExponentialDecay(tf.optimizers.schedules.LearningRateSchedule):
    """This schedule combines a linear warmup with an exponential decay."""

    def __init__(self, learning_rate, warmup_steps, decay_steps, decay_rate):
        super().__init__()
        self._input_config_settings = {"learning_rate": learning_rate, "warmup_steps": warmup_steps,
                                       "decay_steps": decay_steps, "decay_rate": decay_rate}
        self.warmup = tf.optimizers.schedules.PolynomialDecay(
            1 / warmup_steps, warmup_steps, end_learning_rate=1)
        self.decay = tf.optimizers.schedules.ExponentialDecay(
            learning_rate, decay_steps, decay_rate)

    def __call__(self, step):
        """Decay lr for step."""
        return self.warmup(step) * self.decay(step)

    def get_config(self):
        """Get config."""
        config = {}
        config.update(self._input_config_settings)
        return config