import os
import cv2
import h5py
import torch
import numpy as np
from glob import glob
from torch.utils.data import Dataset, DataLoader

from .normalize import get_norm_stats

import IPython
e = IPython.embed


class ACTDataset(Dataset):
    def __init__(self, args, norm_stats):
        super().__init__()
        self.num_queries = args.num_queries
        self.dataset_dir = args.dataset_dir
        self.camera_names = args.camera_names
        self.norm_stats = norm_stats
        self.image_data, self.qpos_data, self.action_seq_data, self.is_pad_data = self.prepare_dataset()


    def __getitem__(self, idx):
        return self.image_data[idx], self.qpos_data[idx], self.action_seq_data[idx], self.is_pad_data[idx]


    def __len__(self):
        return self.qpos_data.shape[0]
    
    
    def prepare_dataset(self):
        file_paths = os.path.join(self.dataset_dir, '*.hdf5')
        file_paths = glob(file_paths)
        total_image = []
        total_qpos = []
        total_action_seq = []
        total_is_pad = []
        for path in file_paths:
            with h5py.File(path, 'r') as f:
                action = f['/action'][()]  # (time_steps, action_dim)
                time_steps = action.shape[0]
                qpos = f['/observations/qpos'][()]  # (time_steps, pos_dim)
                images = []
                for cam_name in self.camera_names:
                    images.append(f[f'/observations/images/{cam_name}'][()])
                # decoder images (if necessary)
                for idx, image in enumerate(images):
                    images_decode = []
                    for i in range(image.shape[0]):
                        image_decode = cv2.imdecode(image[i], 1)
                        images_decode.append(image_decode)
                    images[idx] = np.stack(images_decode, axis=0)        
                # concatenate images
                image = np.stack(images, axis=1)  # (time_steps, num_camera, h, w, c)
                # normalize actions and joint positions
                action = ((action - self.norm_stats["action_mean"]) / self.norm_stats["action_std"]).squeeze()
                qpos = ((qpos - self.norm_stats["qpos_mean"]) / self.norm_stats["qpos_std"]).squeeze()
                # action sequence zero padding
                zero_pad = np.zeros((self.num_queries - 1, action.shape[1]), dtype=np.float32)
                action = np.concatenate([action, zero_pad], axis=0)
                is_pad = np.zeros(action.shape[0])
                is_pad[time_steps: ] = 1  # define where sequences of zero padding are
                # transform nd.array to torch.tensor
                image = torch.from_numpy(image).permute(0, 1, 4, 2, 3)  # (time_steps, num_camera, c, h, w)
                qpos = torch.from_numpy(qpos).float()
                action = torch.from_numpy(action).float()
                is_pad = torch.from_numpy(is_pad).bool()
                # normalize images pixel intensity to [0, 1] (if necessary)
                image = image / 255.0
                ### idx (time_steps, num_queries): [[0, 1, 2...seq-1], [1, 2, 3...seq], [2, 3, 4...seq+1],...]
                idx = torch.stack([torch.arange(i, i + self.num_queries) for i in range(time_steps)], dim=0)
                action_seq = action[idx, :]  # (time_steps, num_queries, dim)
                
                total_image.append(image)
                total_qpos.append(qpos)
                total_action_seq.append(action_seq)
                total_is_pad.append(is_pad)
                
        image_data = torch.cat(total_image, dim=0)
        qpos_data = torch.cat(total_qpos, dim=0)
        action_seq_data = torch.cat(total_action_seq, dim=0)
        is_pad_data = torch.cat(total_is_pad, dim=0)
        
        return image_data, qpos_data, action_seq_data, is_pad_data


def load_data(args):
    # obtain normalization stats for qpos and action
    norm_stats = get_norm_stats(args)
    # Construct dataset and dataloader
    dataset = ACTDataset(args, norm_stats)
    dataloader = DataLoader(dataset, batch_size=args.batch, shuffle=True, pin_memory=True, num_workers=1, prefetch_factor=1)
   
    return dataloader, norm_stats
