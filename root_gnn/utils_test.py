"""
utils for testing trained tf model
"""

import tensorflow as tf
from graph_nets import utils_tf

import yaml
import sklearn.metrics
import os
import numpy as np

from . import utils_train
from . import prepare
from . import get_model

import matplotlib.pyplot as plt

ckpt_name = 'checkpoint_{:05d}.ckpt'

fontsize=16
minor_size = 14

def create_trained_model(config_name, input_ckpt=None):
    """
    @config: configuration for train_nx_graph
    """
    # load configuration file
    config = utils_train.load_config(config_name)
    config_tr = config['train']

    log_every_seconds       = config_tr['time_lapse']
    batch_size = n_graphs   = config_tr['batch_size']   # need optimization
    num_processing_steps_tr = config_tr['n_iters']      ## level of message-passing
    prod_name = config['prod_name']
    if input_ckpt is None:
        input_ckpt = os.path.join(config['output_dir'], prod_name)


    # generate inputs
    generate_input_target = prepare.inputs_generator(config['data']['output_nxgraph_dir'], n_train_fraction=0.8)

    # build TF graph
    tf.reset_default_graph()
    model = get_model(config['model']['name'])

    input_graphs, target_graphs = generate_input_target(n_graphs)
    input_ph  = utils_tf.placeholders_from_data_dicts(input_graphs, force_dynamic_num_graphs=True)
    target_ph = utils_tf.placeholders_from_data_dicts(target_graphs, force_dynamic_num_graphs=True)

    output_ops_tr = model(input_ph, num_processing_steps_tr)

    def evaluator(iteration, n_test_graphs=10):
        try:
            sess.close()
        except NameError:
            pass

        sess = tf.Session()
        saver = tf.train.Saver()
        saver.restore(sess, os.path.join(input_ckpt, ckpt_name.format(iteration)))
        odds = []
        tdds = []
        for _ in range(n_test_graphs):
            feed_dict = utils_train.create_feed_dict(generate_input_target, batch_size, input_ph, target_ph, is_trained=False)
            predictions = sess.run({
                "outputs": output_ops_tr,
                'target': target_ph
            }, feed_dict=feed_dict)
            output = predictions['outputs'][-1]
            target = predictions['target']
            odd, tdd = utils_train.eval_output(target, output)
            odds.append(odd)
            tdds.append(tdd)
        return np.concatenate(odds), np.concatenate(tdds)

    return evaluator


def plot_metrics(odd, tdd, odd_th=0.5, tdd_th=0.5):
    y_pred, y_true = (odd > odd_th), (tdd > tdd_th)
    accuracy  = sklearn.metrics.accuracy_score(y_true, y_pred)
    precision = sklearn.metrics.precision_score(y_true, y_pred)
    recall    = sklearn.metrics.recall_score(y_true, y_pred)

    print('Accuracy:            %.4f' % accuracy)
    print('Precision (purity):  %.4f' % precision)
    print('Recall (efficiency): %.4f' % recall)

    fpr, tpr, _ = sklearn.metrics.roc_curve(y_true, odd)


    fig, axs = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)
    axs = axs.flatten()
    ax0, ax1, ax2, ax3 = axs

    # Plot the model outputs
    # binning=dict(bins=50, range=(0,1), histtype='step', log=True)
    binning=dict(bins=50, histtype='step', log=True)
    ax0.hist(odd[y_true==False], label='fake', **binning)
    ax0.hist(odd[y_true], label='true', **binning)
    ax0.set_xlabel('Model output', fontsize=fontsize)
    ax0.tick_params(width=2, grid_alpha=0.5, labelsize=minor_size)
    ax0.legend(loc=0)

    # Plot the ROC curve
    auc = sklearn.metrics.auc(fpr, tpr)
    ax1.plot(fpr, tpr)
    ax1.plot([0, 1], [0, 1], '--')
    ax1.set_xlabel('False positive rate', fontsize=fontsize)
    ax1.set_ylabel('True positive rate', fontsize=fontsize)
    ax1.set_title('ROC curve, AUC = %.4f' % auc)
    ax1.tick_params(width=2, grid_alpha=0.5, labelsize=minor_size)

    p, r, t = sklearn.metrics.precision_recall_curve(y_true, odd)
    ax2.plot(t, p[:-1], label='purity')
    ax2.plot(t, r[:-1], label='efficiency')
    ax2.set_xlabel('Cut on model score', fontsize=fontsize)
    ax2.tick_params(width=2, grid_alpha=0.5, labelsize=minor_size)
    ax2.legend()

    ax3.plot(p, r)
    ax3.set_xlabel('Purity', fontsize=fontsize)
    ax3.set_ylabel('Efficiency', fontsize=fontsize)
    ax3.tick_params(width=2, grid_alpha=0.5, labelsize=minor_size)

    plt.savefig('roc_graph_nets.eps')



import time
time_format = '%d %b %Y %H:%M:%S'
get2nd = lambda x: x.split()[1]

def read_log(file_name):
    time_info = []
    data_info = []
    itime = -1
    with open(file_name) as f:
        for line in f:
            if line[0] != '#':
                tt = time.strptime(line[:-1], time_format)
                time_info.append(tt)
                data_info.append([])
                itime += 1
            else:
                items = line.split(',')
                try:
                    iteration = int(get2nd(items[0]))
                except ValueError:
                    continue
                time_consumption = float(get2nd(items[1]))
                loss_train = float(get2nd(items[2]))
                loss_test  = float(get2nd(items[3]))
                precision  = float(get2nd(items[4]))
                recall     = float(get2nd(items[5]))
                data_info[itime].append([iteration, time_consumption, loss_train,
                                      loss_test, precision, recall])
    return data_info, time_info

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

fontsize = 16
minor_size = 14
def plot_log_info(info, name, axs=None, with_test=False):
    if type(info) is not 'numpy.ndarray':
        info = np.array(info)
    df = pd.DataFrame(info, columns=['iteration', 'time', 'loss_train', 'loss_test', 'precision', 'recall'])

    # make plots
    if axs is None:
        fig, axs = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)
        axs = axs.flatten()

    y_labels = ['Time [s]', 'Training Loss', 'Precision', 'Recall']
    y_data   = ['time', 'loss_train', 'precision', 'recall']
    x_label = 'Iterations'
    x_data = 'iteration'
    for ib, values in enumerate(zip(y_data, y_labels)):
        ax = axs[ib]
        df.plot(x=x_data, y=values[0], ax=ax, label=name)
        if values[0] == 'loss_train' and with_test:
            df.plot(x=x_data, y='loss_test', ax=ax, label='TEST')
        ax.set_ylabel(values[1], fontsize=fontsize)
        ax.set_xlabel(x_label, fontsize=fontsize)
        ax.tick_params(width=2, grid_alpha=0.5, labelsize=minor_size)
        ax.legend(fontsize=fontsize)

    return axs