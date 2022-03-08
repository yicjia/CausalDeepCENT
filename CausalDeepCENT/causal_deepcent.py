# -*- coding: utf-8 -*-
"""Causal_DeepCENT.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jEtjaxlTLPID2QKTCvMbHJzoojntdTyz
"""

import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import torch.nn.functional as F
from torch.autograd import Variable
import torch.distributions as dist

from sklearn.linear_model import LogisticRegression

import math
import csv
import os
import time

if torch.cuda.is_available():  
  dev = "cuda:0" 
else:  
  dev = "cpu"  
device = torch.device(dev) 


class Net(nn.Module):
    def __init__(self, n_feature, num_layers, node, dropout, drop_factor = 1):
        super(Net, self).__init__()
        # input layer
        layers = [nn.Linear(n_feature, node),
                  nn.BatchNorm1d(node),
                  nn.ReLU()]
        # hidden layers
        node_temp = node
        for i in range(0, num_layers):
            node_temp0 = max(4, int(node_temp / (drop_factor**i)))
            node_temp1 = max(4, int(node_temp0 / drop_factor))
            layers += [nn.Linear(node_temp0, node_temp1),
                       nn.BatchNorm1d(node_temp1),
                       nn.ReLU(),
                       nn.Dropout(p=dropout)]
        layers += [nn.ReLU()]
        # output layer
        layers += [nn.Linear(node_temp1, 1)]
        self.seq = nn.Sequential(*layers) 

    def forward(self, inputs):
        return self.seq(inputs)  


def getIPW(y, x):
    model = LogisticRegression(solver='liblinear').fit(x, y)
    p = model.predict_proba(x)[:, 1]
    w = y/p+(1-y)/(1-p)
    return w


def weighted_mse_loss(pred, obs, delta, weight, lambda1):
    mse = delta*((pred - obs) ** 2)

    ind = pred < obs
    delta0 = 1 - delta
    p = ind * delta0 * (obs - pred)**2 
    return ((mse+lambda1*p)*weight).mean()


def Causal_DeepCENT(train_dataset, test_dataset, num_feature, num_layers, node, dropout, lr, lambda1, num_epoch, batch_size, seed=123, T=100):
    torch.manual_seed(seed)

    train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    test_loader = DataLoader(dataset=test_dataset, batch_size=len(test_dataset))

    model = Net(n_feature=num_feature, num_layers = num_layers, node=node, dropout=dropout)
    model.to(device)

    optimizer = optim.Adam(model.parameters(), lr=lr,weight_decay=1e-8)


    # Trianing
    epoch_loss_train = []
    for e in range(1, num_epoch+1):
        epoch_loss = 0

        model.train()
        for X_train_batch, y_train_batch, E_train_batch, W_train_batch in train_loader:
            optimizer.zero_grad()
        
            y_train_pred = model(X_train_batch)
            mseloss = weighted_mse_loss(y_train_pred, y_train_batch.unsqueeze(1), E_train_batch.unsqueeze(1), W_train_batch.unsqueeze(1),lambda1)
            train_loss = mseloss 
            train_loss.backward()
            optimizer.step()

    
    # Predicting train
    train_loader1 = DataLoader(dataset=train_dataset, batch_size=len(train_dataset))
    y_pred_list0 = []
    with torch.no_grad():
        model.eval()
        for X_batch, y_batch, E_batch, W_batch in train_loader1:
            X_batch = X_batch.to(device)
            # y_test_pred = torch.exp(model(X_batch))
            y_test_pred = model(X_batch)
            y_pred_list0.append(y_test_pred.cpu().numpy())
    y_pred_list0 = [a.squeeze().tolist() for a in y_pred_list0]
    y_pred_list0 = sum(y_pred_list0, [])

    # Predicting test
    with torch.no_grad():
        model.train() 
        result = []
        for _ in range(T): 
            y_pred_list = [] 
            for X_batch, y_batch, E_batch in test_loader:
                y_test_pred = model(X_batch)
                y_pred_list.append(y_test_pred.cpu().numpy())
                y_pred_list = [a.squeeze().tolist() for a in y_pred_list]
                y_pred_list = sum(y_pred_list, [])
            result.append(y_pred_list)
        
        result = np.array(result)
        y_test_pred_mean = result.mean(axis=0).reshape(-1,)
        y_test_pred_sd = result.std(axis=0).reshape(-1,)
        y_pred_list_upper = y_test_pred_mean + 1.96*y_test_pred_sd
        y_pred_list_lower = y_test_pred_mean - 1.96*y_test_pred_sd

    
    return y_pred_list0, y_test_pred_mean,y_pred_list_upper, y_pred_list_lower
