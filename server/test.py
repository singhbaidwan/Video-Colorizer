import os.path as osp
import os
import glob
import cv2
import numpy as np
import torch
import RRDBNet_arch as arch
import subprocess
model_path = '/Users/dalveersingh/Downloads/College/testing capstone/weights-superresolution/RRDB_ESRGAN_x4.pth'  # models/RRDB_ESRGAN_x4.pth OR models/RRDB_PSNR_x4.pth
device = torch.device('cpu')  # if you want to run on CPU, change 'cuda' -> cpu
# device = torch.device('cpu')
base_dir = '/Users/dalveersingh/Downloads/College/testing capstone/data_upload'
test_img_folder = base_dir+"/Result"
final_img_folder = base_dir+"/Final_Result"
subprocess.run(
    ["mkdir","{}".format(final_img_folder)]
)
model = arch.RRDBNet(3, 3, 64, 23, gc=32)
model.load_state_dict(torch.load(model_path), strict=True)
model.eval()
model = model.to(device)

print('Model path {:s}. \nTesting...'.format(model_path))

idx = 0
for file in os.listdir(test_img_folder):
    path = test_img_folder+"/"+file
    # read images
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    img = img * 1.0/255
    img = torch.from_numpy(np.transpose(img[:, :, [2, 1, 0]], (2, 0, 1))).float()
    img_LR = img.unsqueeze(0)
    img_LR = img_LR.to(device)

    with torch.no_grad():
        output = model(img_LR).data.squeeze().float().cpu().clamp_(0, 1).numpy()
    output = np.transpose(output[[2, 1, 0], :, :], (1, 2, 0))
    output = (output * 255.0).round()
    cv2.imwrite(final_img_folder+'/{}.jpg'.format(file), output)