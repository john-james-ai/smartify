#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# ================================================================================================ #
# Project    : Deep Learning with Tensorflow                                                       #
# Version    : 0.1.0                                                                               #
# Filename   : /visualize.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john.james.ai.studio@gmail.com                                                      #
# URL        : https://github.com/john-james-ai/tensorflow-deep-learning                           #
# ------------------------------------------------------------------------------------------------ #
# Created    : Thursday July 21st 2022 03:31:27 am                                                 #
# Modified   : Thursday July 21st 2022 04:03:12 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : BSD 3-clause "New" or "Revised" License                                             #
# Copyright  : (c) 2022 John James                                                                 #
# ================================================================================================ #
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------------------------ #
def plot_loss(history, ylim=None):
    """Plots training and validation loss from the history object of a fitted model."""
    plt.plot(history.history["loss"], label="loss")
    plt.plot(history.history["val_loss"], label="val_loss")
    if ylim:
        plt.ylim(ylim)
    plt.xlabel("Epoch")
    plt.ylabel("Error")
    plt.legend()
    plt.grid(True)
