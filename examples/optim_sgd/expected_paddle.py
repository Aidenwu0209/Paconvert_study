import paddle

conv = paddle.nn.Conv2d(1, 1, 3)
optimizer = paddle.optimizer.SGD(
    parameters=conv.parameters(), learning_rate=0.5, weight_decay=0.0
)
