import numpy as np
import time
import utils
import matplotlib.pyplot as plt
import torch
import model
import torch.optim as optim
 # chamfer distance for calculating point cloud distance

import numpy as np
from scipy.spatial import KDTree

def chamfer_distance(xyz1, xyz2):
    r_xyz1 = torch.sum(xyz1 * xyz1, dim=2, keepdim=True)  # (B,N,1)
    r_xyz2 = torch.sum(xyz2 * xyz2, dim=2, keepdim=True)  # (B,M,1)
    mul = torch.matmul(xyz2, xyz1.permute(0,2,1))         # (B,M,N)
    dist_matrix = r_xyz2 - 2 * mul + r_xyz1.permute(0,2,1)
    dist1 = dist_matrix.min(dim=1)[0].mean()
    dist2 = dist_matrix.min(dim=2)[0].mean()
    return (dist1 + dist2) / 2
    # (B,M,N)
    # return dist

batch_size = 32
output_folder = "output/" # folder path to save the results
save_results = True # save the results to output_folder
use_GPU = True # use GPU, False to use CPU
latent_size = 128 #

from Dataloaders import GetDataLoaders

pc_array = np.load("data/chair_set.npy")
print(pc_array.shape)

# load dataset from numpy array and divide 90%-10% randomly for train and test sets
train_loader, test_loader = GetDataLoaders(npArray=pc_array, batch_size=batch_size)

# Assuming all models have the same size, get the point size from the first model
point_size = len(train_loader.dataset[0])
print(point_size)

net = model.PointCloudAE(point_size,latent_size)

if(use_GPU):
    device = torch.device("cuda:0")
    if torch.cuda.device_count() > 1: # if there are multiple GPUs use all
        net = torch.nn.DataParallel(net)
else:
    device = torch.device("cpu")

net = net.to(device)


optimizer = optim.Adam(net.parameters(), lr=0.0005)


def train_epoch():
    epoch_loss = 0
    for i, data in enumerate(train_loader):
        optimizer.zero_grad()

        data = data.to(device)
        output = net(data.permute(0, 2, 1))  # transpose data for NumberxChannelxSize format
        loss = chamfer_distance(data, output)
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

    return epoch_loss / i


def tes_batch(data):  # test with a batch of inputs
    with torch.no_grad():
        data = data.to(device)
        output = net(data.permute(0, 2, 1))
        loss = chamfer_distance(data, output)

    return loss.item(), output.cpu()


def tes_epoch(): # test with all test set
    with torch.no_grad():
        epoch_loss = 0
        for i, data in enumerate(test_loader):
            loss, output = tes_batch(data)
            epoch_loss += loss

    return epoch_loss/i

if(save_results):
    utils.clear_folder(output_folder)

train_loss_list = []
test_loss_list = []

for i in range(1001):

    startTime = time.time()

    train_loss = train_epoch()  # train one epoch, get the average loss
    train_loss_list.append(train_loss)

    test_loss = tes_epoch()  # test with test set
    test_loss_list.append(test_loss)

    epoch_time = time.time() - startTime

    writeString = "epoch " + str(i) + " train loss : " + str(train_loss) + " test loss : " + str(
        test_loss) + " epoch time : " + str(epoch_time) + "\n"
    print(writeString)
    # plot train/test loss graph
    # plt.plot(train_loss_list, label="Train")
    # plt.plot(test_loss_list, label="Test")
    # plt.legend()

    if (save_results):  # save all outputs to the save folder

        # write the text output to file
        with open(output_folder + "prints.txt", "a") as file:
            file.write(writeString)

        # update the loss graph
        plt.savefig(output_folder + "loss.png")
        plt.close()

        # save input/output as image file
        if (i % 50 == 0):
            test_samples = next(iter(test_loader))
            loss, test_output = tes_batch(test_samples)
            utils.plotPCbatch(test_samples, test_output, show=False, save=True,
                              name=(output_folder + "epoch_" + str(i)))
    #
    # else:  # display all outputs
    #
    #     test_samples = next(iter(test_loader))
    #     loss, test_output = tes_batch(test_samples)
    #     utils.plotPCbatch(test_samples, test_output)
    #
    #     print(writeString)
    #
    #     plt.show()