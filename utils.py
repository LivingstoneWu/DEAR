import random

import matplotlib

matplotlib.use('Agg')
import numpy as np
import pandas as pd
import torch
from torchvision import datasets, transforms
import torchvision.transforms.functional
from torch.utils.data import TensorDataset, DataLoader, Dataset
from PIL import Image
import os
from torchvision.datasets.utils import verify_str_arg


def draw_recon(x, x_recon):
    x_l, x_recon_l = x.tolist(), x_recon.tolist()
    result = [None] * (len(x_l) + len(x_recon_l))
    result[::2] = x_l
    result[1::2] = x_recon_l
    return torch.FloatTensor(result)


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def denorm(x):
    out = (x + 1) / 2
    return out.clamp_(0, 1)


def write_config_to_file(config, save_path):
    with open(os.path.join(save_path, 'config.txt'), 'w') as file:
        for arg in vars(config):
            file.write(str(arg) + ': ' + str(getattr(config, arg)) + '\n')

class RandomRotation90:
    def __call__(self, x):
        angles = [0, 90, 180, 270]
        angle = random.choice(angles)
        return torchvision.transforms.functional.rotate(x, angle)


# + unlabelled
# class FloodDataset(Dataset):
#     def __init__(self, annotation_path, data_dir, unlabelled_data_dir, sampling_size=256) -> None:
#         # by default, annotated images will start with "pre_" or "post_"
#         self.data_dir = data_dir
#         self.annotations = pd.read_csv(annotation_path)
#         self.sampling_size = sampling_size
#         # transform, with 256x256 resize and augmentation, normalization
#         self.transform = transforms.Compose([
#             transforms.Resize((sampling_size, sampling_size)),
#             # transforms.RandomHorizontalFlip(),
#             # transforms.RandomVerticalFlip(),
#             transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
#             # can add random gaussian noise in the future, leave as is for now
#         ])
#         self.unlabelled_image_paths = [os.path.join(unlabelled_data_dir + "PRE/", f) for f in os.listdir(unlabelled_data_dir + "PRE/")] \
#                                     + [os.path.join(unlabelled_data_dir + "POST/", f) for f in os.listdir(unlabelled_data_dir + "POST/")]
#         self.labelled_size = self.annotations.shape[0]
#         self.unlabelled_size = len(self.unlabelled_image_paths)
#
#     def __len__(self) -> int:
#         return self.labelled_size + self.unlabelled_size
#
#     def __getitem__(self, idx):
#         # case labelled:
#         if idx < self.labelled_size:
#             img_path = os.path.join(self.data_dir, self.annotations.iat[idx, 0] + ".tif")
#             labels = torch.tensor(self.annotations.iloc[idx, 1:].apply(pd.to_numeric).to_numpy(), dtype=torch.float32)
#         # unlabelled:
#         else:
#             img_path = self.unlabelled_image_paths[idx - self.labelled_size]
#             # hard-coded label numbers
#             labels = torch.full((7,), -1, dtype=torch.float32)
#         image_tensor = torch.from_numpy(np.array(Image.open(img_path).convert('RGB'))).permute((2, 0, 1)).float()
#         # transform
#         image_tensor = self.transform(image_tensor)
#         if image_tensor.shape != (3, self.sampling_size, self.sampling_size):
#             print(img_path)
#             print(image_tensor.shape)
#         return image_tensor, labels



# no unlabelled

class FloodDataset(Dataset):
    def __init__(self, annotation_path, data_dir, unlabelled_data_dir, sampling_size=256) -> None:
        # by default, annotated images will start with "pre_" or "post_"
        self.data_dir = data_dir
        self.annotations = pd.read_csv(annotation_path)
        self.sampling_size = sampling_size
        # transform, with 256x256 resize and augmentation, normalization
        self.transform = transforms.Compose([
            transforms.Resize((sampling_size, sampling_size)),
            # transforms.RandomHorizontalFlip(),
            # transforms.RandomVerticalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
            # can add random gaussian noise in the future, leave as is for now
        ])
        self.unlabelled_image_paths = [os.path.join(unlabelled_data_dir + "PRE/", f) for f in os.listdir(unlabelled_data_dir + "PRE/")] \
                                    + [os.path.join(unlabelled_data_dir + "POST/", f) for f in os.listdir(unlabelled_data_dir + "POST/")]
        self.labelled_size = self.annotations.shape[0]
        self.unlabelled_size = len(self.unlabelled_image_paths)

    def __len__(self) -> int:
        return self.labelled_size

    def __getitem__(self, idx):

        img_path = os.path.join(self.data_dir, self.annotations.iat[idx, 0] + ".tif")
        labels = torch.tensor(self.annotations.iloc[idx, 1:].apply(pd.to_numeric).to_numpy(), dtype=torch.float32)

        image_tensor = Image.open(img_path).convert('RGB')
        # transform
        image_tensor = self.transform(image_tensor)
        if image_tensor.shape != (3, self.sampling_size, self.sampling_size):
            print(img_path)
            print(image_tensor.shape)
        return image_tensor, labels

def make_dataloader(args):
    test_loader = None
    train_loader = None
    if args.dataset == 'celeba':

        trans_f = transforms.Compose([
            transforms.CenterCrop(128),
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
        train_set = datasets.CelebA(args.data_dir, split='train', download=False, transform=trans_f)
        train_loader = torch.utils.data.DataLoader(train_set, batch_size=args.batch_size, shuffle=True,
                                                   pin_memory=False,
                                                   drop_last=True, num_workers=args.dataloader_workers)

    elif 'pendulum' in args.dataset:
        train_set = dataload_withlabel(args.data_dir, image_size=args.image_size,
                                       mode='train', sup_prop=args.sup_prop)
        train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, drop_last=True,
                                  num_workers=args.dataloader_workers)

    elif 'flood' in args.dataset:
        train_set = FloodDataset(args.annotation_path, args.data_dir, args.unlabelled_data_dir, args.sampling_size)
        train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, pin_memory=True, drop_last=True,
                                  num_workers=args.dataloader_workers)

    return train_loader, test_loader


def check_for_CUDA(sagan_obj):
    if not sagan_obj.config.disable_cuda and torch.cuda.is_available():
        print("CUDA is available!")
        sagan_obj.device = torch.device('cuda')
        sagan_obj.config.dataloader_args['pin_memory'] = True
    else:
        print("Cuda is NOT available, running on CPU.")
        sagan_obj.device = torch.device('cpu')

    if torch.cuda.is_available() and sagan_obj.config.disable_cuda:
        print("WARNING: You have a CUDA device, so you should probably run without --disable_cuda")


class dataload_withlabel(torch.utils.data.Dataset):
    def __init__(self, root, label_file=None, image_size=64, mode="train", sup_prop=1., num_sample=0):
        # label_file: 'pendulum_label_downstream.txt'

        self.label_file = label_file
        if label_file is not None:
            self.attrs_df = pd.read_csv(os.path.join(root, label_file))
            # attr = self.attrs_df[:, [1,2,3,7,5]]
            self.split_df = pd.read_csv(os.path.join(root, label_file))
            splits = self.split_df['partition'].values
            split_map = {
                "train": 0,
                "valid": 1,
                "test": 2,
                "all": None,
            }
            split = split_map[verify_str_arg(mode.lower(), "split",
                                             ("train", "valid", "test", "all"))]
            mask = slice(None) if split is None else (splits == split)
            self.mask = mask
            np.random.seed(2)
            if num_sample > 0:
                idxs = [i for i, x in enumerate(mask) if x]
                not_sample = np.random.permutation(idxs)[num_sample:]
                mask[not_sample] = False
            self.attrs_df = self.attrs_df.values
            self.attrs_df[self.attrs_df == -1] = 0
            self.attrs_df = self.attrs_df[mask][:, [0, 1, 2, 3, 6]]
            self.imglabel = torch.as_tensor(self.attrs_df.astype(np.float))
            self.imgs = []
            for i in range(3):
                mode1 = list(split_map.keys())[i]
                root1 = root + mode1
                imgs = os.listdir(root1)
                self.imgs += [os.path.join(root, mode1, k) for k in imgs]
            self.imgs = np.array(self.imgs)[mask]
        else:
            root = root + mode
            imgs = os.listdir(root)
            self.imgs = [os.path.join(root, k) for k in imgs]
            self.imglabel = [list(map(float, k[:-4].split("_")[1:])) for k in imgs]
        self.transforms = transforms.Compose([transforms.Resize((image_size, image_size)), transforms.ToTensor()])
        np.random.seed(2)
        self.n = len(self.imgs)
        self.available_label_index = np.random.choice(self.n, int(self.n * sup_prop), replace=0)

    def __getitem__(self, idx):
        img_path = self.imgs[idx]
        if not (idx in self.available_label_index):
            label = torch.zeros(4).long() - 1
        else:
            if self.label_file is None:
                label = torch.from_numpy(np.asarray(self.imglabel[idx]))
            else:
                label = self.imglabel[idx]
        pil_img = Image.open(img_path).convert('RGB')
        array = np.array(pil_img)
        array1 = np.array(label)
        label = torch.from_numpy(array1)
        data = torch.from_numpy(array)
        if self.transforms:
            data = self.transforms(pil_img)
        else:
            pil_img = np.asarray(pil_img).reshape(96, 96, 3)
            data = torch.from_numpy(pil_img)
        return data, label.float()

    def __len__(self):
        return len(self.imgs)
