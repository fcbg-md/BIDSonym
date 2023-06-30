import os
import json
import shutil
import numpy as np
from glob import glob
import pandas as pd
import nibabel as nib
from shutil import move
import nipype.pipeline.engine as pe
from nipype import Function
from nipype.interfaces import utility as niu
from nipype.interfaces.fsl import BET

from bids import BIDSLayout

from ._logs import logger

def move_file(source_path, destination_path):
    # Create necessary folders in the destination path
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    # Move the file to the destination path
    shutil.move(source_path, destination_path)


def copy_no_deid(bids_dir, file):
    # no deid layout
    nodeid_path = os.path.join(bids_dir, "sourcedata", "bidsonym")
    nodeid_layout =  BIDSLayout(nodeid_path, validate=False)
    source_path = file.path
    # Build new path
    nodeied_file_path = nodeid_layout.build_path(file.entities)
    # Move file
    move_file(source_path, nodeied_file_path)
    return(nodeied_file_path)


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
    logger.info('working on %s' % subject_label)

    # deid layout
    layout = BIDSLayout(bids_dir, validate=False)
    # no deid layout
    nodeid_path = os.path.join(bids_dir, "sourcedata", "bidsonym")
    nodeid_layout =  BIDSLayout(nodeid_path, validate=False)

    json_files = layout.get(subject=subject_label, suffix='json')
    edited_files = list()
    for file in json_files:
        file_path = file.path
        edited = False
        with open(file_path, 'r') as json_file:
            meta_data = json.load(json_file)
            for field in fields_del:
                if field in meta_data:
                    meta_data[field] = 'deleted_by_bidsonym'
                    edited = True
        if edited:
            logger.info("Editing file: %s" % file_path)
            edited_files.append(file)
            # Build new path
            entities = file.entities
            nodeied_file_path = nodeid_layout.build_path(entities)
            move_file(file_path, nodeied_file_path)
            with open(file_path, 'w') as json_output_file:
                json.dump(meta_data, json_output_file, indent=4)


def brain_extraction_nb(image, subject_label, bids_dir):
    """
    Setup nobrainer brainextraction command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    bids_dir : str
        Path to BIDS root directory.
    """

    import os
    from subprocess import check_call

    outfile = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s" % subject_label,
                           image[image.rfind('/')+1:image.rfind('.nii')] + '_brainmask_desc-nondeid.nii.gz')

    cmd = ['nobrainer',
           'predict',
           '--model=/opt/nobrainer/models/trained-models/neuronets/brainy/0.1.0/weights/brain-extraction-unet-128iso-model.h5',
           '--verbose',
           image,
           outfile,
           ]
    check_call(cmd)
    return(outfile)


def run_brain_extraction_nb(image, subject_label, bids_dir):
    """
    Setup and run nobrainer brainextraction workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    bids_dir : str
        Path to BIDS root directory.
    """

    brainextraction_wf = pe.Workflow('brainextraction_wf')
    inputnode = pe.Node(niu.IdentityInterface(['in_file']),
                        name='inputnode')
    brainextraction = pe.Node(Function(input_names=['image', 'subject_label', 'bids_dir'],
                                       output_names=['outfile'],
                                       function=brain_extraction_nb),
                              name='brainextraction')
    brainextraction_wf.connect([(inputnode, brainextraction, [('in_file', 'image')])])
    inputnode.inputs.in_file = image
    brainextraction.inputs.subject_label = subject_label
    brainextraction.inputs.bids_dir = bids_dir
    brainextraction_wf.run()


def run_brain_extraction_bet(image, frac, subject_label, bids_dir):
    """
    Setup and FSLs brainextraction (BET) workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    frac : float
        Fractional intensity threshold (0 - 1).
    outfile : str
        Name of the defaced file.
    bids_dir : str
        Path to BIDS root directory.
    """

    import os

    outfile = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s" % subject_label,
                           image[image.rfind('/')+1:image.rfind('.nii')] + '_brainmask_desc-nondeid.nii.gz')
    dir_name = os.path.dirname(outfile)
    os.makedirs(dir_name, exist_ok=True)

    brainextraction_wf = pe.Workflow('brainextraction_wf')
    inputnode = pe.Node(niu.IdentityInterface(['in_file']),
                        name='inputnode')
    bet = pe.Node(BET(mask=False), name='bet')
    brainextraction_wf.connect([
        (inputnode, bet, [('in_file', 'in_file')]),
        ])
    inputnode.inputs.in_file = image
    bet.inputs.frac = float(frac)
    bet.inputs.out_file = outfile
    brainextraction_wf.run()
    return(outfile)


def deface_t2w(image, warped_mask, outfile):
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
    from nibabel import load, Nifti1Image
    from nilearn.image import math_img

    # functionality copied from pydeface
    infile_img = load(image)
    warped_mask_img = load(warped_mask)
    warped_mask_img = math_img('img > 0', img=warped_mask_img)
    try:
        outdata = infile_img.get_fdata().squeeze() * warped_mask_img.get_fdata()
    except ValueError:
        tmpdata = np.stack([warped_mask_img.get_fdata()] *
                           infile_img.get_fdata().shape[-1], axis=-1)
        outdata = infile_img.fget_data() * tmpdata

    masked_brain = Nifti1Image(outdata, infile_img.get_affine(),
                               infile_img.get_header())
    masked_brain.to_filename(outfile)