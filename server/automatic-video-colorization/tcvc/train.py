from __future__ import print_function

import argparse
import os
from os.path import join

import math
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable
from torch.utils.data import DataLoader

from tcvc.data import create_iterator, get_dataset
from tcvc.loss import AdversarialLoss, StyleLoss, PerceptualLoss
from tcvc.networks import define_G, define_D, print_network
from tcvc.util import stitch_images, postprocess

if __name__ == "__main__":
    os.environ[
        "CUDA_VISIBLE_DEVICES"
    ] = "0"  # Ensure that we only use one GPU, not multiple

    # Training settings
    parser = argparse.ArgumentParser(
        description="Training script for Automatic Temporally Coherent Video Colorization"
    )
    parser.add_argument(
        "--dataset-path",
        dest="dataset",
        required=True,
        help="Path to a folder that contains the training set (image frames)",
    )
    parser.add_argument(
        "--include-subfolders",
        dest="include_subfolders",
        action="store_true",
        help="Include images from subfolders in the specified dataset path.",
    )
    parser.add_argument(
        "--input-style",
        dest="input_style",
        type=str,
        choices=["line_art", "greyscale"],
        help="line_art (canny edge detection) or greyscale",
        default="greyscale",
    )
    parser.add_argument("--logfile", required=False, default="training_logs.dat")
    parser.add_argument("--checkpoint", required=False, help="load pre-trained?")
    parser.add_argument("--batchSize", type=int, default=8, help="training batch size")
    parser.add_argument(
        "--testBatchSize", type=int, default=1, help="testing batch size"
    )
    parser.add_argument(
        "--nEpochs", type=int, default=50, help="number of epochs to train for"
    )
    parser.add_argument("--input_nc", type=int, default=1, help="input image channels")
    parser.add_argument(
        "--output_nc", type=int, default=3, help="output image channels"
    )
    parser.add_argument(
        "--ngf", type=int, default=64, help="generator filters in first conv layer"
    )  # better to also be 128?
    parser.add_argument(
        "--ndf", type=int, default=64, help="discriminator filters in first conv layer"
    )  # increasing filters in discriminator made slight diff (not used with inpaint generator)
    parser.add_argument(
        "--lr", type=float, default=0.0001, help="Learning Rate. Default=0.0001"
    )
    parser.add_argument(
        "--beta1", type=float, default=0, help="beta1 for adam. default=0"
    )
    parser.add_argument(
        "--cpu", action="store_true", help="Use CPU instead of CUDA (GPU)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=0,
        help="number of threads for data loader to use",
    )
    parser.add_argument(
        "--seed", type=int, default=123, help="random seed to use. Default=123"
    )
    parser.add_argument(
        "--L1lamb", type=int, default=10, help="weight on L1 term in objective"
    )
    parser.add_argument(
        "--Stylelamb", type=int, default=1000, help="weight on Style term in objective"
    )
    parser.add_argument(
        "--Contentlamb", type=int, default=1, help="weight on Content term in objective"
    )
    parser.add_argument(
        "--Adversariallamb",
        type=int,
        default=0.1,
        help="weight on Adv term in objective",
    )
    opt = parser.parse_args()

    print(opt)

    if not opt.cpu and not torch.cuda.is_available():
        raise Exception("No GPU found, please run without --cuda")

    cudnn.benchmark = True

    torch.manual_seed(opt.seed)
    if not opt.cpu:
        torch.cuda.manual_seed(opt.seed)
    final_path = "/kaggle/working"
    print("===> Loading datasets")
    train_set = get_dataset(
        opt.dataset,
        use_line_art=opt.input_style == "line_art",
        include_subfolders=opt.include_subfolders,
    )
    # TODO: Add a separate argument for test set path. Do not use the same paths for training and testing
    test_set = get_dataset(
        opt.dataset,
        use_line_art=opt.input_style == "line_art",
        include_subfolders=opt.include_subfolders,
    )

    training_data_loader = DataLoader(
        dataset=train_set,
        num_workers=opt.threads,
        batch_size=opt.batchSize,
        shuffle=True,
    )
    testing_data_loader = DataLoader(
        dataset=test_set,
        num_workers=opt.threads,
        batch_size=opt.testBatchSize,
        shuffle=False,
    )

    sample_iterator = create_iterator(6, test_set)

    print("===> Building model")
    netG = define_G(opt.input_nc, opt.output_nc, opt.ngf, False, [0])
    netD = define_D(opt.input_nc + opt.output_nc, opt.ndf, False, [0])

    # criterionGAN = GANLoss()
    criterionGAN = AdversarialLoss()
    criterionSTYLE = StyleLoss()
    criterionCONTENT = PerceptualLoss()
    criterionL1 = nn.L1Loss()
    criterionMSE = nn.MSELoss()

    # setup optimizer
    optimizerG = optim.Adam(netG.parameters(), lr=opt.lr, betas=(opt.beta1, 0.999))
    optimizerD = optim.Adam(
        netD.parameters(), lr=opt.lr * 0.1, betas=(opt.beta1, 0.999)
    )

    print("---------- Networks initialized -------------")
    print_network(netG)
    print_network(netD)
    print("-----------------------------------------------")

    real_a = torch.FloatTensor(opt.batchSize, opt.input_nc, 128,128)
    real_b = torch.FloatTensor(opt.batchSize, opt.output_nc, 128,128)
    prev_b = torch.FloatTensor(opt.batchSize, opt.output_nc, 128, 128)

    if not opt.cpu:
        netD = netD.cuda()
        netG = netG.cuda()
        criterionGAN = criterionGAN.cuda()
        criterionL1 = criterionL1.cuda()
        criterionSTYLE = criterionSTYLE.cuda()
        criterionCONTENT = criterionCONTENT.cuda()
        criterionMSE = criterionMSE.cuda()
        real_a = real_a.cuda()
        real_b = real_b.cuda()
        prev_b = prev_b.cuda()

    real_a = Variable(real_a)
    real_b = Variable(real_b)
    prev_b = Variable(prev_b)

    # in terms of steps rather than iterations
    # no iteration penalty
    # while statement vs if
    # LSGAN
    def train(epoch):

        for iteration, batch in enumerate(training_data_loader, 1):
            # forward
            real_a_cpu, real_b_cpu, prev_b_cpu = batch[0], batch[1], batch[2]
            # print("real_a_cpu",real_a_cpu.size())
            with torch.no_grad():
                real_a.resize_(real_a_cpu.size()).copy_(real_a_cpu)
                real_b.resize_(real_b_cpu.size()).copy_(real_b_cpu)
                prev_b.resize_(prev_b_cpu.size()).copy_(prev_b_cpu)

            input_joined = torch.cat((real_a, prev_b), 1)
            # print("input_jouned",input_joined.shape)
            fake_b = netG(input_joined)
            # print("fake_b",fake_b.shape)

            ############################
            # (1) Update D network: maximize log(D(x,y)) + log(1 - D(x,G(x)))
            ###########################

            optimizerD.zero_grad()

            # train with fake
            fake_ab = torch.cat((real_a, prev_b, fake_b), 1)
            pred_fake = netD.forward(fake_ab.detach())
            loss_d_fake = criterionGAN(pred_fake, False, True)

            # train with real
            real_ab = torch.cat((real_a, prev_b, real_b), 1)
            pred_real = netD.forward(real_ab)
            loss_d_real = criterionGAN(pred_real, True, True)

            # Combined loss
            loss_d = (loss_d_fake + loss_d_real) * 0.5

            loss_d.backward()

            # Only update Dis parameters every 12 iterations give Gen a chance to learn (still
            # not quite right)
            # Stop Discriminator if loss less than 0.5
            if iteration == 1 or iteration % 12 == 0:
                optimizerD.step()

            # optimizerD.step()

            ############################
            # (2) Update G network: maximize log(D(x,G(x))) + L1(y,G(x))
            ##########################
            optimizerG.zero_grad()

            # First, G(A) should fake the discriminator

            fake_ab = torch.cat((real_a, prev_b, fake_b), 1)
            pred_fake = netD.forward(fake_ab)
            loss_g_gan = criterionGAN(pred_fake, True, False)

            # Second, G(A) = B
            loss_g_l1 = criterionL1(fake_b, real_b) * opt.L1lamb
            loss_g = loss_g_gan + loss_g_l1

            loss_g_style = criterionSTYLE(fake_b, real_b) * opt.Stylelamb
            loss_g = loss_g + loss_g_style

            loss_g_content = criterionCONTENT(fake_b, real_b) * opt.Contentlamb
            loss_g = loss_g + loss_g_content

            loss_g.backward()

            optimizerG.step()

            # prog.add(len(batch), values=logs)

            if iteration % 25 == 0:
                logs = [
                    ("epoc", epoch),
                    ("iter", iteration),
                    ("Loss_G", loss_g.item()),
                    ("Loss_D", loss_d.item()),
                    ("Loss_G_adv", loss_g_gan.item()),
                    ("Loss_G_L1", loss_g_l1.item()),
                    ("Loss_G_style", loss_g_style.item()),
                    ("Loss_G_content", loss_g_content.item()),
                    ("Loss_D_Real", loss_d_real.item()),
                    ("Loss_D_Fake", loss_d_fake.item()),
                ]
                log_train_data(logs)

            if iteration % 250 == 0:
                sample(iteration)

            print(
                "===> Epoch[{}]({}/{}): Loss_D: {:.4f} Loss_G: {:.4f} LossD_Fake: {:.4f}"
                " LossD_Real: {:.4f}  LossG_Adv: {:.4f} LossG_L1: {:.4f} LossG_Style {:.4f}"
                " LossG_Content {:.4f}".format(
                    epoch,
                    iteration,
                    len(training_data_loader),
                    loss_d,
                    loss_g,
                    loss_d_fake,
                    loss_d_real,
                    loss_g_gan,
                    loss_g_l1,
                    loss_g_style,
                    loss_g_content,
                )
            )

    def sample(iteration):
        with torch.no_grad():
            input_image, target, prev_frame = next(sample_iterator)
            # input_image = Variable(input_image, requires_grad = False)
            if not opt.cpu:
                input_image = input_image.cuda()
                target = target.cuda()
                prev_frame = prev_frame.cuda()
            pred_input = torch.cat((input_image, prev_frame), 1)
            prediction = netG(pred_input)
            prediction = postprocess(prediction)
            input_image = postprocess(input_image)
            target = postprocess(target)
        img = stitch_images(input_image, target, prediction)
        samples_dir = join(final_path, "samples")
        os.makedirs(samples_dir, exist_ok=True)

        sample_filename = str(epoch) + "_" + str(iteration).zfill(5) + ".png"
        print("\nsaving sample " + sample_filename + " - learning rate: " + str(opt.lr))
        img.save(os.path.join(samples_dir, sample_filename))

    def load(checkpoint_path, netG, netD, optimizerG, optimizerD):
        ckpt = torch.load(checkpoint_path)
        netG.load_state_dict(ckpt["netG_state_dict"])
        netD.load_state_dict(ckpt["netD_state_dict"])
        optimizerG.load_state_dict(ckpt["optimizerG_state_dict"])
        optimizerD.load_state_dict(ckpt["optimizerD_state_dict"])
        return netG, netD, optimizerG, optimizerD

    def log_train_data(loginfo):
        log_dir = join(opt.dataset, "/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = log_dir + "/" + opt.logfile
        with open(log_file, "a") as f:
            f.write("%s\n" % " ".join([str(item[1]) for item in loginfo]))

    def test():
        avg_psnr = 0
        for batch in testing_data_loader:
            input_image, target, prev_frame = (
                Variable(batch[0], volatile=True),
                Variable(batch[1], volatile=True),
                Variable(batch[2], volatile=True),
            )
            if not opt.cpu:
                input_image = input_image.cuda()
                target = target.cuda()
                prev_frame = prev_frame.cuda()
            pred_input = torch.cat((input_image, prev_frame), 1)
            prediction = netG(pred_input)
            # prediction = netG(input_image)
            mse = criterionMSE(prediction, target)
            psnr = 10 * math.log10(1 / mse.data[0])
            avg_psnr += psnr
        print("===> Avg. PSNR: {:.4f} dB".format(avg_psnr / len(testing_data_loader)))

    def checkpoint(epoch):
        checkpoint_folder = os.path.join(final_path, "checkpoint")
        os.makedirs(checkpoint_folder, exist_ok=True)
        net_g_model_out_path = os.path.join(
            checkpoint_folder, "netG_LA2_weights_epoch_{}.pth".format(epoch)
        )
        net_d_model_out_path = os.path.join(
            checkpoint_folder, "netD_LA2_weights_epoch_{}.pth".format(epoch)
        )
        torch.save({"generator": netG.state_dict()}, net_g_model_out_path)
        torch.save({"discriminator": netD.state_dict()}, net_d_model_out_path)
        print("Checkpoint saved to {}".format(checkpoint_folder))

    for epoch in range(1, opt.nEpochs + 1):
        train(epoch)
        # test()
        checkpoint(epoch)

    def run():
        torch.multiprocessing.freeze_support()
        print("loop")

    if __name__ == "__main__":
        run()
