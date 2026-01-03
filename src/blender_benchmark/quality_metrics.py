# quality_metrics.py
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr


def load_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img)


def compute_psnr(img1_path, img2_path):
    img1 = load_image(img1_path)
    img2 = load_image(img2_path)
    return psnr(img1, img2)


def compute_ssim(img1_path, img2_path):
    img1 = load_image(img1_path)
    img2 = load_image(img2_path)
    score, _ = ssim(img1, img2, channel_axis=2, full=True)
    return score
