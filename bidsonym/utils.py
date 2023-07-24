import json
import os
import shutil

from bids import BIDSLayout

from ._logs import logger


def move_file(source_path, destination_path):
    # Create necessary folders in the destination path
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    # Move the file to the destination path
    shutil.move(source_path, destination_path)


def copy_no_deid(bids_dir, file, relpath="sourcedata/bidsonym"):
    """
    Copy file to a new location without de-identification.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.$
    file : BIDSFile
        File to copy.
    relpath : str
        Relative path of the derivatives BIDS directory.
    """
    # no deid layout
    nodeid_path = os.path.join(bids_dir, relpath)
    os.makedirs(nodeid_path, exist_ok=True)
    nodeid_layout = BIDSLayout(nodeid_path, validate=False)
    # path of source file
    source_path = file.path
    # Build new path
    nodeied_file_path = nodeid_layout.build_path(file.entities)
    # Move file
    move_file(source_path, nodeied_file_path)
    return nodeied_file_path


def del_meta_data(bids_dir, subject_label, fields_del):
    """
    Delete values from specified keys in meta-data json files.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.
    subject_label : str
        Label of subject to operate on (without 'sub-').
    fields_del : list
        List of meta-data keys ('str') which value should be removed.
    """
    logger.info("working on %s" % subject_label)

    # deid layout
    layout = BIDSLayout(bids_dir, validate=False)
    # no deid layout
    nodeid_path = os.path.join(bids_dir, "sourcedata", "bidsonym")
    nodeid_layout = BIDSLayout(nodeid_path, validate=False)

    json_files = layout.get(subject=subject_label, suffix="json")
    edited_files = list()
    for file in json_files:
        file_path = file.path
        edited = False
        with open(file_path, "r") as json_file:
            meta_data = json.load(json_file)
            for field in fields_del:
                if field in meta_data:
                    meta_data[field] = "deleted_by_bidsonym"
                    edited = True
        if edited:
            logger.info("Editing file: %s" % file_path)
            edited_files.append(file)
            # Build new path
            entities = file.entities
            nodeied_file_path = nodeid_layout.build_path(entities)
            move_file(file_path, nodeied_file_path)
            with open(file_path, "w") as json_output_file:
                json.dump(meta_data, json_output_file, indent=4)


def deface_t2w(in_file, warped_mask, out_file):
    """
    Deface T2w image using the defaced T1w image as
    deface mask.

    Parameters
    ----------
    image : str
        Path to image.
    warped_mask : str
        Path to warped defaced T1w image.
    outfile: str
        Name of the defaced file.
    """
    import numpy as np
    from nibabel import Nifti1Image, load
    from nilearn.image import math_img

    # functionality copied from pydeface
    infile_img = load(in_file)
    warped_mask_img = load(warped_mask)
    warped_mask_img = math_img("img > 0", img=warped_mask_img)
    try:
        outdata = infile_img.get_fdata().squeeze()
        outdata *= warped_mask_img.get_fdata()
    except ValueError:
        tmpdata = np.stack(
            [warped_mask_img.get_fdata()] * infile_img.get_fdata().shape[-1],
            axis=-1,
        )
        outdata = infile_img.fget_data() * tmpdata

    masked_brain = Nifti1Image(
        outdata, infile_img.affine, infile_img.header
    )
    masked_brain.to_filename(out_file)
    return out_file
