This is the PyTorch implementation of [_Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware_](https://arxiv.org/abs/2304.13705). Code in this repository is copied from the [official codebase](https://github.com/tonyzhaozh/act) and simplified such that minimal requirements are demanded. Also, sufficient annotations are added to help readers better understand the algorithm.

## Usage
### 1. Collect human demonstrations.
```bash
cd utils
python collect_data.py
```
### 2. Train the policy.
```bash
python train.py --dataset_dir <YOUR_DATASET_ROOT>
```
### 3. Evaluate the policy.
```bash
python test.py --checkpoint <YOUR_CHECKPOINT_PATH>
```
