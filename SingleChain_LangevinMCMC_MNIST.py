#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 12:32:34 2019

@author: ashray

python 3.6 --  working great

rnn with mcmc in torch

"""

#  %reset
#  %reset -sf


import torchvision
import torch.nn.functional as F
import torchvision.transforms as transforms
import torch
import torch.nn as nn
import numpy as np
import random
import math
import copy
import os
import matplotlib.pyplot as plt


input_size = 320
hidden_size = 50
num_classes = 10
batch_size = 25
device = 'cpu'

def data_load(data='train'):
    # trainsize = 200
    # testsize = 40

    if data == 'test':
        samples = torchvision.datasets.MNIST(root='./mnist', train=False, download=True,
                                             transform=torchvision.transforms.Compose([transforms.ToTensor(),
                                                                                       torchvision.transforms.Normalize(
                                                                                           (0.1307,), (0.3081,))]))
        size = 200
        a, _ = torch.utils.data.random_split(samples, [size, len(samples) - size])

    else:
        samples = torchvision.datasets.MNIST(root='./mnist', train=True, download=True, transform=torchvision.transforms.Compose([transforms.ToTensor(),
                                                     torchvision.transforms.Normalize((0.1307,), (0.3081,))]))
        size = 500
        a, _ = torch.utils.data.random_split(samples, [size, len(samples) - size])

    data_loader = torch.utils.data.DataLoader(a,
                                              batch_size=batch_size,
                                              shuffle=True)
    return data_loader

def f(): raise Exception("Found exit()")


class Model(nn.Module):

    # Defining input size, hidden layer size, output size and batch size respectively
    def __init__(self, topo, lrate):
        super(Model, self).__init__()

        self.conv1 = nn.Conv2d(1, 32, 5, 1)
        self.conv2 = nn.Conv2d(32, 64, 5, 1)
        self.fc1 = nn.Linear(1024, 10)
        # self.fc2 = nn.Linear(128, 10)

        self.batch_size = batch_size
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.sigmoid = nn.Sigmoid()
        self.topo = topo
        self.los = 0
        self.softmax = nn.Softmax(dim=1)
        self.criterion = torch.nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=lrate)



        self.conv1 = nn.Conv2d(1, 32, 5, 1)
        self.conv2 = nn.Conv2d(32, 64, 5, 1)
        self.fc1 = nn.Linear(1024, 10)
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        #self.fc2 = nn.Linear(128, 10)

        self.batch_size = batch_size
        self.sigmoid = nn.Sigmoid()
        self.topo = topo
        self.los = 0
        self.softmax = nn.Softmax(dim=1)
        self.criterion = torch.nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=lrate)
        self.drop_out = nn.Dropout()

    def sigmoid(self, z):
        return 1 / (1 + torch.exp(-z))

    def forward(self, x):
        x = self.conv1(x)
        # print("def")
        x = F.max_pool2d(x, 2)
        # x = F.relu(x)
        # x = nn.Dropout2d(x)
        x = self.conv2(x)
        x = F.max_pool2d(x, 2)
        # x = F.relu(x)
        x = torch.flatten(x, 1)
        x = F.relu(x)
        # print("X Shape")
        # print(x.shape)
        x = self.fc1(x)
        # x = nn.Sigmoid(x)
        # x=F.relu(x)
        # x = self.fc2(x)
        # x = F.relu(x)
        return x

    def evaluate_proposal(self, data, w=None):
        self.los = 0
        if w is not None:
            self.loadparameters(w)
        y_pred = torch.zeros((len(data), self.batch_size))
        prob = torch.zeros((len(data), self.batch_size, self.topo[2]))
        for i, sample in enumerate(data, 0):
            inputs, labels = sample
            a = copy.deepcopy(self.forward(inputs).detach())
            _, predicted = torch.max(a.data, 1)
            # y_pred[i] = torch.argmax(copy.deepcopy(a),dim=1)
            y_pred[i] = predicted
            # print(a)
            # print(a.shape)
            # f()
            b = copy.deepcopy(a)
            prob[i] = self.softmax(b)
            # prob[i] = self.softmax(a)
            # print(predicted.shape)
            # print(labels.shape)
            loss = self.criterion(a, labels)
            self.los += loss
        return y_pred, prob

    def langevin_gradient(self, x, w=None):
        if w is not None:
            self.loadparameters(w)
        # only one epoch
        self.los = 0
        # print(self.state_dict()['fc.weight'][0])
        for i, sample in enumerate(x, 0):
            inputs, labels = sample
            outputs = self.forward(inputs)
            _, predicted = torch.max(outputs.data, 1)
            loss = self.criterion(outputs, labels)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            # if (i % 50 == 0):
            # print(loss.item(), ' is loss', i)
            self.los += copy.deepcopy(loss.item())
        # print(lo,' is loss')
        return copy.deepcopy(self.state_dict())

    def getparameters(self, w=None):
        l = np.array([1, 2])
        dic = {}
        if w is None:
            dic = self.state_dict()
        else:
            dic = copy.deepcopy(w)
        for name in sorted(dic.keys()):
            l = np.concatenate((l, np.array(copy.deepcopy(dic[name])).reshape(-1)), axis=None)
        l = l[2:]
        return l

    def dictfromlist(self, param):
        dic = {}
        i = 0
        for name in sorted(self.state_dict().keys()):
            dic[name] = torch.FloatTensor(param[i:i + (self.state_dict()[name]).view(-1).shape[0]]).view(
                self.state_dict()[name].shape)
            i += (self.state_dict()[name]).view(-1).shape[0]
        # self.loadparameters(dic)
        return dic

    def loadparameters(self, param):
        self.load_state_dict(param)

    def addnoiseandcopy(self, mea, std_dev):
        dic = {}
        w = self.state_dict()
        for name in (w.keys()):
            dic[name] = copy.deepcopy(w[name]) + torch.zeros(w[name].size()).normal_(mean=mea, std=std_dev)
        self.loadparameters(dic)
        return dic


class MCMC:
    def __init__(self, samples, topology, use_langevin_gradients, lr, batch_size):
        self.samples = samples
        self.topology = topology
        self.rnn = Model(topology, lr)
        self.traindata = data_load(data='train')
        self.testdata = data_load(data='test')
        self.topology = topology
        self.use_langevin_gradients = use_langevin_gradients
        self.batch_size = batch_size
        self.l_prob=0.5
        # ----------------

    def rmse(self, predictions, targets):
        return self.rnn.los.item()

    def likelihood_func(self, rnn, data, w=None):
        y = torch.zeros((len(data), self.batch_size))
        for i, dat in enumerate(data, 0):
            inputs, labels = dat
            y[i] = labels
        if w is not None:
            fx, prob = rnn.evaluate_proposal(data, w)
        else:
            fx, prob = rnn.evaluate_proposal(data)
        # rmse = self.rmse(fx,y)
        rmse = copy.deepcopy(self.rnn.los) / len(data)
        lhood = 0
        for i in range(len(data)):
            for j in range(self.batch_size):
                for k in range(self.topology[2]):
                    if k == y[i][j]:
                        if prob[i,j,k] == 0:
                            lhood+=0
                        else:
                            lhood += np.log(prob[i, j, k])
        return [lhood, fx, rmse]

    def prior_likelihood(self, sigma_squared, w_list):
        part1 = -1 * ((len(w_list)) / 2) * np.log(sigma_squared)
        part2 = 1 / (2 * sigma_squared) * (sum(np.square(w_list)))
        log_loss = part1 - part2
        return log_loss


    def accuracy(self, data):
        # Test the model
        correct = 0
        total = 0
        for images, labels in data:
            # images = images.reshape(-1, sequence_length, input_size).to(device)
            labels = labels.to(device)
            outputs = self.rnn(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
        return 100 * correct / total


    def sampler(self):
        samples = self.samples
        rnn = self.rnn
        w = rnn.state_dict()
        w_size = len(rnn.getparameters(w))
        rmse_train = np.zeros(samples)
        rmse_test = np.zeros(samples)
        acc_train = np.zeros(samples)
        acc_test = np.zeros(samples)

        likelihood_proposal_array = np.zeros(samples)
        likelihood_array=np.zeros(samples)
        diff_likelihood_array=np.zeros(samples)
        weight_array=np.zeros(samples)
        weight_array1=np.zeros(samples)
        weight_array2=np.zeros(samples)
        sum_value_array=np.zeros(samples)


        eta = 0
        w_proposal = np.random.randn(w_size)
        w_proposal = rnn.dictfromlist(w_proposal)
        step_w = 0.05
        train = self.traindata  # data_load(data='train')
        test = self.testdata  # data_load(data= 'test')
        sigma_squared = 25
        nu_1 = 0
        nu_2 = 0
        delta_likelihood = 0.5  # an arbitrary position
        prior_current = self.prior_likelihood(sigma_squared, rnn.getparameters(w))


        [likelihood, pred_train, rmsetrain] = self.likelihood_func(rnn, train)
        [_, pred_test, rmsetest] = self.likelihood_func(rnn, test)

        # Beginning Sampling using MCMC RANDOMWALK
        y_test = torch.zeros((len(test), self.batch_size))
        for i, dat in enumerate(test, 0):
            inputs, labels = dat
            y_test[i] = copy.deepcopy(labels)
        y_train = torch.zeros((len(train), self.batch_size))
        for i, dat in enumerate(train, 0):
            inputs, labels = dat
            y_train[i] = copy.deepcopy(labels)

        trainacc = 0
        testacc = 0

        num_accepted = 0
        langevin_count = 0
        init_count = 0
        rmse_train[0] = rmsetrain
        rmse_test[0] = rmsetest
        acc_train[0] = self.accuracy(train)
        acc_test[0] = self.accuracy(test)
        likelihood_proposal_array[0]=0
        likelihood_array[0]=0
        diff_likelihood_array[0]=0
        weight_array[0]=0
        weight_array1[0] = 0
        weight_array2[0] = 0
        sum_value_array[0]=0

        #pytorch_total_params = sum(p.numel() for p in rnn.parameters() if p.requires_grad)
        #print(pytorch_total_params)
        # acc_train[0] = 50.0
        # acc_test[0] = 50.0

        # print('i and samples')
        for i in range(samples):  # Begin sampling --------------------------------------------------------------------------

            lx = np.random.uniform(0, 1, 1)
            old_w = rnn.state_dict()
            #and (lx < self.l_prob)
            if (self.use_langevin_gradients is True) and (lx < self.l_prob):
                w_gd = rnn.langevin_gradient(train)  # Eq 8
                w_proposal = rnn.addnoiseandcopy(0, step_w)  # np.random.normal(w_gd, step_w, w_size) # Eq 7
                w_prop_gd = rnn.langevin_gradient(train)
                wc_delta = (rnn.getparameters(w) - rnn.getparameters(w_prop_gd))
                wp_delta = (rnn.getparameters(w_proposal) - rnn.getparameters(w_gd))
                sigma_sq = step_w
                first = -0.5 * np.sum(wc_delta * wc_delta) / sigma_sq  # this is wc_delta.T  *  wc_delta /sigma_sq
                second = -0.5 * np.sum(wp_delta * wp_delta) / sigma_sq
                diff_prop = first - second
                diff_prop = diff_prop
                langevin_count = langevin_count + 1
            else:
                diff_prop = 0
                w_proposal = rnn.addnoiseandcopy(0, step_w)  # np.random.normal(w, step_w, w_size)


            [likelihood_proposal, pred_train, rmsetrain] = self.likelihood_func(rnn, train)
            [likelihood_ignore, pred_test, rmsetest] = self.likelihood_func(rnn, test)



            prior_prop = self.prior_likelihood(sigma_squared, rnn.getparameters(w_proposal))  # takes care of the gradients

            diff_likelihood = likelihood_proposal - likelihood
            #diff_likelihood = diff_likelihood*-1
            diff_prior = prior_prop - prior_current

            likelihood_proposal_array[i] = likelihood_proposal
            likelihood_array[i] = likelihood
            diff_likelihood_array[i] = diff_likelihood



            #print("\n\n")
            #print("Likelihood Proposal")
            #print(likelihood_proposal)
            #print("\n\n")


            #print("\n\n")
            #print("Likelihood")
            #print(likelihood)
            #print("\n\n")

            #print("Diff_Likelihood")
            #print(diff_likelihood)
            #print("\n\n")

            #print("Diff_Prior")
            #print(diff_prior)
            #print("\n\n")

            #print("Diff_Prop")
            #print(diff_prop)
            #print("\n\n")

            #print("Sum Number")
            #print(diff_likelihood + diff_prior + diff_prop)
            #print("\n\n")
            #+ diff_prior + diff_prop

            #try:
            #    mh_prob = min(1, math.exp(diff_likelihood))
            #except OverflowError as e:
            #    mh_prob = 1

            sum_value=diff_likelihood + diff_prior + diff_prop
            u = np.log(random.uniform(0, 1))

            sum_value_array[i]=sum_value

            #print("Sum_Value")
            #print(sum_value)
            #print("\n\n")

            #print("U")
            #print(u)
            #print("\n\n")
            #print("MH_Prob")
            #print(mh_prob)
            #print("\n\n")

            if u < sum_value:
                num_accepted = num_accepted + 1
                likelihood = likelihood_proposal
                prior_current = prior_prop
                w = copy.deepcopy(w_proposal)  # rnn.getparameters(w_proposal)
                acc_train1 = self.accuracy(train)
                acc_test1 = self.accuracy(test)
                print (i, rmsetrain, rmsetest, acc_train1, acc_test1, 'accepted')
                rmse_train[i] = rmsetrain
                rmse_test[i] = rmsetest
                acc_train[i,] = acc_train1
                acc_test[i,] = acc_test1

            else:
                w = old_w
                rnn.loadparameters(w)
                acc_train1 = self.accuracy(train)
                acc_test1 = self.accuracy(test)
                print (i, rmsetrain, rmsetest, acc_train1, acc_test1, 'rejected')
                #rmse_train[i] = rmsetrain
                #rmse_test[i] = rmsetest
                #acc_train[i,] = acc_train1
                #acc_test[i,] = acc_test1
                rmse_train[i,] = rmse_train[i - 1,]
                rmse_test[i,] = rmse_test[i - 1,]
                acc_train[i,] = acc_train[i - 1,]
                acc_test[i,] = acc_test[i - 1,]

            ll=rnn.getparameters()
            #print(ll[0])
            weight_array[i]=ll[0]
            weight_array1[i] = ll[100]
            weight_array2[i] = ll[50000]


        print ((num_accepted * 100 / (samples * 1.0)), '% was Accepted')

        print ((langevin_count * 100 / (samples * 1.0)), '% was Langevin')

        return acc_train, acc_test, rmse_train, rmse_test, sum_value_array, weight_array, weight_array1, weight_array2



def main():
    outres = open('resultspriors.txt', 'w')

    topology = [input_size, hidden_size, num_classes]

    numSamples = 1000
    ulg = True

    learnr=0.01
    burnin =0.25


    mcmc = MCMC(numSamples, topology, ulg, learnr, batch_size)  # declare class
    acc_train, acc_test, rmse_train, rmse_test, sva, wa, wa1, wa2 = mcmc.sampler()

    acc_train=acc_train[int(numSamples*burnin):]
    #print(acc_train)
    acc_test=acc_test[int(numSamples*burnin):]
    rmse_train=rmse_train[int(numSamples*burnin):]
    rmse_test=rmse_test[int(numSamples*burnin):]
    sva=sva[int(numSamples*burnin):]
    #print(lpa)

    print("\n\n\n\n\n\n\n\n")
    print("Mean of RMSE Train")
    print(np.mean(rmse_train))
    print("\n")
    print("Mean of Accuracy Train")
    print(np.mean(acc_train))
    print("\n")
    print("Mean of RMSE Test")
    print(np.mean(rmse_test))
    print("\n")
    print("Mean of Accuracy Test")
    print(np.mean(acc_test))
    print ('sucessfully sampled')

    problemfolder = 'mnist_torch_single_chain'
    os.makedirs(problemfolder)


    x = np.linspace(0, int(numSamples-numSamples*burnin), num=int(numSamples-numSamples*burnin))
    x1 = np.linspace(0, numSamples, num=numSamples)

    plt.plot(x1, wa, label='Weight[0]')
    plt.legend(loc='upper right')
    plt.title("Weight[0] Trace")
    plt.savefig('mnist_torch_single_chain' + '/weight[0]_samples.png')
    plt.clf()

    plt.plot(x1, wa1, label='Weight[100]')
    plt.legend(loc='upper right')
    plt.title("Weight[100] Trace")
    plt.savefig('mnist_torch_single_chain' + '/weight[100]_samples.png')
    plt.clf()

    plt.plot(x1,wa2, label='Weight[50000]')
    plt.legend(loc='upper right')
    plt.title("Weight[50000] Trace")
    plt.savefig('mnist_torch_single_chain' + '/weight[50000]_samples.png')
    plt.clf()

    plt.plot(x, sva, label='Sum_Value')
    plt.legend(loc='upper right')
    plt.title("Sum Value Over Samples")
    plt.savefig('mnist_torch_single_chain'+'/sum_value_samples.png')
    plt.clf()


    #plt.plot(x, acc_train, label='Train')
    #plt.legend(loc='upper right')
    #plt.title("Accuracy Train Values Over Samples")
    #plt.savefig('mnist_torch_single_chain' + '/accuracy_samples.png')
    #plt.clf()

    fig, ax1 = plt.subplots()

    color = 'tab:red'
    ax1.set_xlabel('Samples')
    ax1.set_ylabel('Accuracy Train', color=color)
    ax1.plot(x, acc_train, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Accuracy Test', color=color)  # we already handled the x-label with ax1
    ax2.plot(x, acc_test, color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    #ax3=ax1.twinx()

    #color = 'tab:green'
    #ax3.set_ylabel('Accuracy Test', color=color)  # we already handled the x-label with ax1
    #ax3.plot(x, acc_test, color=color)
    #ax3.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.savefig('mnist_torch_single_chain' + '/superimposed_acc.png')
    plt.clf()

    fig1, ax4 = plt.subplots()

    color = 'tab:red'
    ax4.set_xlabel('Samples')
    ax4.set_ylabel('RMSE Train', color=color)
    ax4.plot(x, rmse_train, color=color)
    ax4.tick_params(axis='y', labelcolor=color)

    ax5 = ax4.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:blue'
    ax5.set_ylabel('RMSE Test', color=color)  # we already handled the x-label with ax1
    ax5.plot(x, rmse_test, color=color)
    ax5.tick_params(axis='y', labelcolor=color)

    #ax6 = ax4.twinx()

    #color = 'tab:green'
    #ax6.set_ylabel('RMSE Test', color=color)  # we already handled the x-label with ax1
    #ax6.plot(x, rmse_test, color=color)
    #ax6.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.savefig('mnist_torch_single_chain' + '/superimposed_rmse.png')
    plt.clf()




if __name__ == "__main__": main()