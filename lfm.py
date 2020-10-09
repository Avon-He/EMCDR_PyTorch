import os
import numpy as np
import pandas as pd
import argparse
import torch
import torch.nn as nn
from time import time

from model import MF


def parse_args():
    parser = argparse.ArgumentParser(description="Latent Factor Model")
    parser.add_argument('--dataset', type=str, default='', help="d")
    parser.add_argument('--mode', type=str, default='s', help="s or t")
    parser.add_argument('--dim', type=int, default=16, help="embedding")
    parser.add_argument('--lr', type=float, default=0.001, help="lr")
    parser.add_argument('--reg', type=float, default=0, help="r")
    parser.add_argument('--epochs', type=int, default=100, help='e')
    parser.add_argument('--batchsize', type=int, default=512, help="b")
    return parser.parse_args()


def default_args():
    return 'Musical_Patio'


def load_data(dataset, mode):
    dp = 'data/%s/%s.csv' % (dataset, mode)
    data = pd.read_csv(dp, ',', names=['u', 'i', 'r', 't'], engine='python')
    data.sort_values(by=['u', 'i'], inplace=True)
    return data


def batch_user(n_user, batch_size):
    for i in range(0, n_user, batch_size):
        yield list(range(i, min(i+batch_size, n_user)))


def ground_truth(data, users, n_item):
    df = data.loc[data['u'].isin(users)].values
    y = np.zeros((len(users), n_item))
    row = df.shape[0]
    for i in range(row):
        y[int(df[i][0])-users[0]][int(df[i][1])] = 1.0
    return y


def train(rmf, opt, mse_loss, users, y):
    out = rmf(users)
    loss = mse_loss(out, y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    return loss.cpu().item()


def main(dataset, mode, dim, lr, reg, epochs, batchsize):
    data = load_data(dataset, mode)
    n_user = data['u'].max() + 1
    n_item = data['i'].max() + 1
    print(n_user, n_item)

    rmf = MF(n_user, n_item, dim)
    opt = torch.optim.Adam(rmf.parameters(), lr=lr, weight_decay=reg)
    mse_loss = nn.MSELoss()

    start = time()
    for epoch in range(epochs):
        loss_sum = 0
        for users in batch_user(n_user, batchsize):
            y = ground_truth(data, users, n_item)
            y = torch.tensor(y).float()
            loss = train(rmf, opt, mse_loss, users, y)
            loss_sum += loss
        print('Epoch %d [%.1f] loss = %f' % (epoch, time()-start, loss_sum))
        start = time()

    mdir = 'pretrain/%s/' % dataset
    mfile = mdir + 'MF_%s.pth.tar' % mode
    if not os.path.exists(mdir):
        os.makedirs(mdir, exist_ok=True)
    torch.save(rmf.state_dict(), mfile)
    print('save [%.1f]' % (time()-start))


if __name__ == '__main__':
    args = parse_args()
    args.dataset = default_args()
    main(args.dataset, args.mode, args.dim, args.lr,
         args.reg, args.epochs, args.batchsize)
