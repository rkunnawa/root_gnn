
import numpy as np
import sklearn.metrics

import tensorflow as tf

from graph_nets import utils_tf
from graph_nets import utils_np

import yaml

def create_loss_ops(target_op, output_ops):
    # only use globals
    loss_ops = [
        tf.losses.log_loss(target_op.globals, output_op.globals)
        for output_op in output_ops
    ]
    return loss_ops

def create_softmax_loss(target_op, output_ops):
    loss_ops = [
        tf.losses.softmax_cross_entropy(target_op.globals, output_op.globals)
        for output_op in output_ops
    ]
    return loss_ops


def make_all_runnable_in_session(*args):
  """Lets an iterable of TF graphs be output from a session as NP graphs."""
  return [utils_tf.make_runnable_in_session(a) for a in args]


def eval_output(target, output):

    tdds = utils_np.graphs_tuple_to_data_dicts(target)
    odds = utils_np.graphs_tuple_to_data_dicts(output)

    test_target = []
    test_pred = []
    for td, od in zip(tdds, odds):
        test_target.append(td['globals'])
        test_pred.append(od['globals'])

    test_target = np.concatenate(test_target, axis=0)
    test_pred   = np.concatenate(test_pred,   axis=0)
    return test_pred, test_target


def compute_matrics(target, output):
    test_pred, test_target = eval_output(target, output)
    thresh = 0.5
    y_pred, y_true = (test_pred > thresh), (test_target > thresh)
    return sklearn.metrics.precision_score(y_true, y_pred), sklearn.metrics.recall_score(y_true, y_pred)

