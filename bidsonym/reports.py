import os

from matplotlib.pyplot import figure
import matplotlib.pyplot as plt
from nilearn.plotting import find_cut_slices, plot_stat_map
import gif2nif

from .utils import move


def nifti_to_gif(input, output=None):
    """ Create a GIF of input image"""
    gif2nif.write_gif_normal(input)
    gif_path = os.path.splitext(input)[0] + '.gif'
    if output:
        os.makedirs(output, exist_ok=True)
        move(gif_path, output)
    return()


def plot_overlay(brainmask, input_path, output_path=None):
    """
    Plot brainmask created from original non-defaced image on defaced image
    to evaluate defacing performance.
    """
    fig = figure(figsize=(15, 5))
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=-0.2, hspace=0)
    for i, e in enumerate(['x', 'y', 'z']):
        ax = fig.add_subplot(3, 1, i + 1)
        cuts = find_cut_slices(input_path, direction=e, n_cuts=12)
        plot_stat_map(brainmask, bg_img=input_path, display_mode=e,
                        cut_coords=cuts, annotate=False, dim=-1, axes=ax, colorbar=False)
    # Save
    if output_path is None:
        pre, _ = os.path.splitext(input_path)
        output_path = pre + '.png'
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    return(output_path)