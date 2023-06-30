from .utils import move


def nifti_to_gif(input, output=None):
    import gif2nif
    import os
    gif2nif.write_gif_normal(input)
    gif_path = os.path.splitext(input)[0] + '.gif'
    if output:
        os.makedirs(output, exist_ok=True)
        move(gif_path, output)
    return()


def plot_overlay(brainmask, image_path, png_path=None):
    """
    Plot brainmask created from original non-defaced image on defaced image
    to evaluate defacing performance.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.
    file : BIDSFILE object
        a BIDSFILE object
    """
    import os
    from matplotlib.pyplot import figure
    import matplotlib.pyplot as plt
    from nilearn.plotting import find_cut_slices, plot_stat_map

    fig = figure(figsize=(15, 5))
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=-0.2, hspace=0)
    for i, e in enumerate(['x', 'y', 'z']):
        ax = fig.add_subplot(3, 1, i + 1)
        cuts = find_cut_slices(image_path, direction=e, n_cuts=12)
        plot_stat_map(brainmask, bg_img=image_path, display_mode=e,
                        cut_coords=cuts, annotate=False, dim=-1, axes=ax, colorbar=False)
    # Save
    if png_path is None:
        pre, _ = os.path.splitext(image_path)
        png_path = pre + '.png'
    else:
        os.makedirs(os.path.dirname(png_path), exist_ok=True)
    plt.savefig(png_path)
    return(png_path)