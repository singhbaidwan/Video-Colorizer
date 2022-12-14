import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable

from tcvc.othernetworks import *
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF
from runpy import run_path
from skimage import img_as_ubyte
from natsort import natsorted
from glob import glob
import cv2
from tqdm import tqdm
import argparse
import numpy as np
def weights_init(m):
    classname = m.__class__.__name__
    if classname.find("Conv") != -1:
        m.weight.data.normal_(0.0, 0.02)
    elif classname.find("BatchNorm2d") != -1 or classname.find("InstanceNorm2d") != -1:
        m.weight.data.normal_(1.0, 0.02)
        m.bias.data.fill_(0)


def define_G(input_nc, output_nc, ngf, use_dropout=True, gpu_ids=None):
    if gpu_ids is None:
        gpu_ids = []
    use_gpu = len(gpu_ids) > 0

    if use_gpu:
        assert torch.cuda.is_available()
    task = 'super_resolution'
    load_arch = run_path("/kaggle/working/MIRNetv2/basicsr/models/archs/mirnet_v2_arch.py")
    parameters = {
      'inp_channels':3,
      'out_channels':3, 
      'n_feat':80,
      'chan_factor':1.5,
      'n_RRG':4,
      'n_MRB':2,
      'height':3,
      'width':2,
      'bias':False,
      'scale':4,
      'task': task
      }
    model = load_arch['MIRNet_v2'](**parameters)
    weights = "/kaggle/working/MIRNetv2/Super_Resolution/pretrained_models/sr_x4.pth"
    checkpoint = torch.load(weights)
    model.cuda()

    model.load_state_dict(checkpoint['params'])
    for param in model.parameters():
      param.requires_grad = False
    # netG = ResnetGenerator(input_nc, output_nc, ngf, norm_layer=norm_layer, use_dropout=use_dropout, n_blocks=9, gpu_ids=gpu_ids)
    netG = InpaintGenerator(model)

    if len(gpu_ids) > 0:
        netG.cuda(gpu_ids[0])
    # netG.apply(weights_init)
    return netG


def define_D(input_nc, ndf, use_sigmoid=True, gpu_ids=None):
    if gpu_ids is None:
        gpu_ids = []
    use_gpu = len(gpu_ids) > 0

    if use_gpu:
        assert torch.cuda.is_available()

    # netD = NLayerDiscriminator(input_nc, ndf, n_layers=3, norm_layer=norm_layer, use_sigmoid=use_sigmoid, gpu_ids=gpu_ids)
    netD = Discriminator(in_channels=7, use_sigmoid=True)
    if use_gpu:
        netD.cuda(gpu_ids[0])
    # netD.apply(weights_init)
    return netD


def print_network(net):
    num_params = 0
    for param in net.parameters():
        num_params += param.numel()
    print(net)
    print("Total number of parameters: %d" % num_params)


class GANLoss(nn.Module):
    """Define the GAN loss which uses either LSGAN or the regular GAN."""
    def __init__(
        self,
        use_lsgan=False,
        target_real_label=1.0,
        target_fake_label=0.0,
        tensor=torch.FloatTensor,
    ):
        super(GANLoss, self).__init__()
        self.real_label = target_real_label
        self.fake_label = target_fake_label
        self.real_label_var = None
        self.fake_label_var = None
        self.Tensor = tensor
        if use_lsgan:
            self.loss = nn.MSELoss()
        else:
            self.loss = nn.BCEWithLogitsLoss()

    def get_target_tensor(self, input_image, target_is_real):
        if target_is_real:
            create_label = (self.real_label_var is None) or (
                self.real_label_var.numel() != input_image.numel()
            )
            if create_label:
                real_tensor = self.Tensor(input_image.size()).fill_(self.real_label)
                self.real_label_var = Variable(real_tensor, requires_grad=False)
            target_tensor = self.real_label_var
        else:
            create_label = (self.fake_label_var is None) or (
                self.fake_label_var.numel() != input_image.numel()
            )
            if create_label:
                fake_tensor = self.Tensor(input_image.size()).fill_(self.fake_label)
                self.fake_label_var = Variable(fake_tensor, requires_grad=False)
            target_tensor = self.fake_label_var
        return target_tensor

    def __call__(self, input_image, target_is_real):
        target_tensor = self.get_target_tensor(input_image, target_is_real)
        return self.loss(input_image, target_tensor.cuda())


class ResnetGenerator(nn.Module):
    """
    Define the generator that consists of Resnet blocks between a few
    downsampling/upsampling operations.
    """
    def __init__(
        self,
        input_nc,
        output_nc,
        ngf=64,
        norm_layer=nn.BatchNorm2d,
        use_dropout=False,
        n_blocks=6,
        gpu_ids=None,
    ):
        assert n_blocks >= 0
        super(ResnetGenerator, self).__init__()
        self.input_nc = input_nc
        self.output_nc = output_nc
        self.ngf = ngf
        if gpu_ids is None:
            self.gpu_ids = []
        else:
            self.gpu_ids = gpu_ids

        model = [
            nn.Conv2d(input_nc, ngf, kernel_size=7, padding=3),
            norm_layer(ngf, affine=True),
            nn.ReLU(True),
        ]

        n_downsampling = 2
        for i in range(n_downsampling):
            mult = 2 ** i
            model += [
                nn.Conv2d(
                    ngf * mult, ngf * mult * 2, kernel_size=3, stride=2, padding=1
                ),
                norm_layer(ngf * mult * 2, affine=True),
                nn.ReLU(True),
            ]

        mult = 2 ** n_downsampling
        for i in range(n_blocks):
            model += [
                ResnetBlock(
                    ngf * mult, "zero", norm_layer=norm_layer, use_dropout=use_dropout
                )
            ]

        for i in range(n_downsampling):
            mult = 2 ** (n_downsampling - i)
            model += [
                nn.ConvTranspose2d(
                    ngf * mult,
                    int(ngf * mult / 2),
                    kernel_size=3,
                    stride=2,
                    padding=1,
                    output_padding=1,
                ),
                norm_layer(int(ngf * mult / 2), affine=True),
                nn.ReLU(True),
            ]

        model += [nn.Conv2d(ngf, output_nc, kernel_size=7, padding=3)]
        model += [nn.Tanh()]

        self.model = nn.Sequential(*model)

    def forward(self, input_image):
        if self.gpu_ids and isinstance(input_image.data, torch.cuda.FloatTensor):
            return nn.parallel.data_parallel(self.model, input_image, self.gpu_ids)
        else:
            return self.model(input_image)



class ResnetBlock(nn.Module):
    """Define a resnet block."""
    def __init__(self, dim, padding_type, norm_layer, use_dropout):
        super(ResnetBlock, self).__init__()
        self.conv_block = self.build_conv_block(
            dim, padding_type, norm_layer, use_dropout
        )

    def build_conv_block(self, dim, padding_type, norm_layer, use_dropout):
        conv_block = []
        assert padding_type == "zero"
        p = 1

        conv_block += [
            nn.Conv2d(dim, dim, kernel_size=3, padding=p),
            norm_layer(dim, affine=True),
            nn.ReLU(True),
        ]
        if use_dropout:
            conv_block += [nn.Dropout(0.5)]
        conv_block += [
            nn.Conv2d(dim, dim, kernel_size=3, padding=p),
            norm_layer(dim, affine=True),
        ]

        return nn.Sequential(*conv_block)

    def forward(self, x):
        out = x + self.conv_block(x)
        return out


# Defines the PatchGAN discriminator.
class NLayerDiscriminator(nn.Module):
    def __init__(
        self,
        input_nc,
        ndf=64,
        n_layers=5,
        norm_layer=nn.BatchNorm2d,
        use_sigmoid=False,
        gpu_ids=None,
    ):
        super(NLayerDiscriminator, self).__init__()
        if gpu_ids is None:
            self.gpu_ids = []
        else:
            self.gpu_ids = gpu_ids

        kw = 5
        padw = int(np.ceil((kw - 1) / 2))
        sequence = [
            nn.Conv2d(input_nc, ndf, kernel_size=kw, stride=2, padding=padw),
            nn.LeakyReLU(0.2, True),
        ]

        nf_mult = 1
        nf_mult_prev = 1
        for n in range(1, n_layers):
            nf_mult_prev = nf_mult
            nf_mult = min(2 ** n, 8)
            sequence += [
                nn.Conv2d(
                    ndf * nf_mult_prev,
                    ndf * nf_mult,
                    kernel_size=kw,
                    stride=2,
                    padding=padw,
                ),
                norm_layer(ndf * nf_mult, affine=True),
                nn.LeakyReLU(0.2, True),
            ]

        nf_mult_prev = nf_mult
        nf_mult = min(2 ** n_layers, 8)
        sequence += [
            nn.Conv2d(
                ndf * nf_mult_prev,
                ndf * nf_mult,
                kernel_size=kw,
                stride=1,
                padding=padw,
            ),
            norm_layer(ndf * nf_mult, affine=True),
            nn.LeakyReLU(0.2, True),
        ]

        sequence += [
            nn.Conv2d(ndf * nf_mult, 1, kernel_size=kw, stride=1, padding=padw)
        ]

        if use_sigmoid:
            sequence += [nn.Sigmoid()]

        self.model = nn.Sequential(*sequence)

    def forward(self, input_image):
        if len(self.gpu_ids) and isinstance(input_image.data, torch.cuda.FloatTensor):
            return nn.parallel.data_parallel(self.model, input_image, self.gpu_ids)
        else:
            return self.model(input_image)
