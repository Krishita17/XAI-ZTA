# save this as test_nn.py in your XAI-ZTA folder and run: python test_nn.py
import numpy as np
import torch
print("1. Imports OK")

from torch.utils.data import DataLoader, TensorDataset
print("2. DataLoader OK")

X = np.random.randn(1000, 10).astype(np.float32)
y = np.random.randint(0, 2, 1000).astype(np.float32)
print("3. Dummy data OK")

dataset = TensorDataset(torch.FloatTensor(X), torch.FloatTensor(y))
loader = DataLoader(dataset, batch_size=64, shuffle=True, num_workers=0)
print("4. DataLoader created OK")

for batch_X, batch_y in loader:
    print("5. DataLoader iteration OK — batch shape:", batch_X.shape)
    break

print("6. ALL GOOD — problem is elsewhere in your pipeline")