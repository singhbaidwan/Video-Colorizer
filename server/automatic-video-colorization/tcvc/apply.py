from __future__ import print_function

import argparse
import os
from runpy import run_path
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from torch.utils.data import DataLoader, SequentialSampler
from tqdm import tqdm

from tcvc.data import get_dataset
from tcvc.gif import make_gif
from tcvc.othernetworks import InpaintGenerator

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pix2pix-PyTorch-implementation")
    parser.add_argument(
        "--model",
        type=str,
        default="tcvc/checkpoint/Temporal/netG_weights_epoch_1.pth",
        help="Path to the generator model file to use",
    )
    parser.add_argument(
        "--input-path",
        dest="input_path",
        type=str,
        required=True,
        help="The path to the folder that contains the images (frames)",
    )
    parser.add_argument(
        "--input-style",
        dest="input_style",
        type=str,
        choices=["line_art", "greyscale"],
        help="line_art (canny edge detection) or greyscale",
        default="line_art",
    )
    parser.add_argument(
        "--cpu", default = True,action="store_true", help="Use CPU instead of CUDA (GPU)"
    )
    parser.add_argument(
        "--make-gif",
        dest="make_gif",
        action="store_true",
        help="Make a GIF with the output frames",
    )
    opt = parser.parse_args()

    val_set = get_dataset(opt.input_path, use_line_art=opt.input_style == "line_art")

    seq_sampler = SequentialSampler(val_set)

    val_data_loader = DataLoader(
        dataset=val_set, num_workers=0, batch_size=1, shuffle=False, sampler=seq_sampler
    )
    task = 'super_resolution'
    load_arch = run_path("/Users/dalveersingh/Downloads/College/testing capstone/app/server/mirnet_v2_arch.py")
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
    m1 = load_arch['MIRNet_v2'](**parameters)
    checkpoint = torch.load(opt.model,map_location = 'cpu')
    netG = InpaintGenerator(m1)
    netG.load_state_dict(checkpoint["generator"])
    # netG.cuda()

    transform_list = [
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
    ]

    transform = transforms.Compose(transform_list)

    result_dir = os.path.join(opt.input_path, "colored")
    # os.makedirs(result_dir, exist_ok=True)

    counter = 0
    with torch.no_grad():
        for batch in tqdm(val_data_loader):
            input_image, target, prev_frame = (batch[0], batch[1], batch[2])
            if not opt.cpu:
                input_image = input_image.cuda()
                target = target.cuda()
                prev_frame = prev_frame.cuda()
            if counter != 0:
                prev_frame = tmp
            pred_input = torch.cat((input_image, prev_frame), 1)
            out = netG(pred_input)
            tmp = out

            if not opt.cpu:
                # Get image from GPU memory
                out = out.cpu()

            # Convert the image to a numpy array
            out_np = out.numpy()[0]

            # Convert the image shape to (height, width, channels)
            out_np = np.transpose(out_np, (1, 2, 0))

            # Remove black borders
            out_np = out_np[2:-2, 2:-2, :]

            # Convert the image to the correct data format for saving
            out_np = (out_np * 255).astype(np.uint8)

            # Save the image
            image_name = "frame{}.png".format(str(counter).zfill(5))
            Image.fromarray(out_np).save(os.path.join("/Users/dalveersingh/Downloads/College/testing capstone/data_upload/Result", image_name))

            counter += 1

    if opt.make_gif:
        print("\nMaking gif...")
        make_gif(result_dir)
