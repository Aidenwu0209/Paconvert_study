import torch

conv = torch.nn.Conv2d(1, 1, 3)
optimizer = torch.optim.SGD(conv.parameters(), 0.5)
