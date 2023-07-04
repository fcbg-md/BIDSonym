import os

import nipype.pipeline.engine as pe
from nipype import Function
from nipype.interfaces import utility as niu
from nipype.interfaces.fsl import BET, FLIRT
from nipype.interfaces.quickshear import Quickshear


def pydeface_cmd(in_file, out_file):
    """
    Setup pydeface command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """

    from subprocess import check_call

    cmd = [
        "pydeface",
        in_file,
        "--out",
        out_file,
        "--force",
    ]
    check_call(cmd)
    return out_file


def run_pydeface(in_file, out_file):
    """
    Setup and run pydeface workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    pydeface = pe.Node(
        Function(
            input_names=["in_file", "out_file"],
            output_names=["out_file"],
            function=pydeface_cmd,
        ),
        name="pydeface",
    )
    pydeface.inputs.in_file = in_file
    pydeface.inputs.out_file = out_file
    results = pydeface.run()
    out_file = results.outputs.out_file
    return out_file


def mri_deface_cmd(in_file, out_file):
    """
    Setup mri_deface command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    from subprocess import check_call
    cmd = [
        "/home/bm/bidsonym/fs_data/mri_deface",
        in_file,
        "/home/bm/bidsonym/fs_data/talairach_mixed_with_skull.gca",
        "/home/bm/bidsonym/fs_data/face.gca",
        out_file,
    ]
    check_call(cmd)
    return out_file


def run_mri_deface(in_file, out_file):
    """
    Setup and run mri_deface workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    mri_deface = pe.Node(
        Function(
            input_names=["in_file", "out_file"],
            output_names=["out_file"],
            function=mri_deface_cmd,
        ),
        name="mri_deface",
    )
    mri_deface.inputs.in_file = in_file
    mri_deface.inputs.out_file = out_file
    results = mri_deface.run()
    out_file = results.outputs.out_file
    return out_file


def run_quickshear(in_file, out_file):
    """
    Setup and run quickshear workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    bet = pe.Node(BET(mask=True, frac=0.5), name="bet")
    quickshear = pe.Node(Quickshear(buff=50), name="quickshear")
    deface_wf.connect(
        [
            (inputnode, bet, [("in_file", "in_file")]),
            (inputnode, quickshear, [("in_file", "in_file")]),
            (bet, quickshear, [("mask_file", "mask_file")]),
        ]
    )
    inputnode.inputs.in_file = in_file
    quickshear.inputs.out_file = out_file
    deface_wf.run()
    return out_file


def mridefacer_cmd(in_file, out_dir):
    """
    Setup mridefacer command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    from subprocess import check_call
    cmd = ["/mridefacer/mridefacer", "--apply", in_file, "--outdir", out_dir]
    check_call(cmd)
    out_file = os.path.join(out_dir, os.path.basename(in_file))
    return out_file


def run_mridefacer(in_file, out_dir):
    """
    Setup and mridefacer workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    os.makedirs(os.path.dirname(out_dir), exist_ok=True)
    mridefacer = pe.Node(
        Function(
            input_names=["in_file", "out_dir"],
            output_names=["out_file"],
            function=mridefacer_cmd,
        ),
        name="mridefacer",
    )
    mridefacer.inputs.in_file = in_file
    mridefacer.inputs.out_dir = out_dir
    results = mridefacer.run()
    out_file = results.outputs.out_file
    return out_file


def deepdefacer_cmd(in_file, out_file, maskfile):
    """
    Setup deepdefacer command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    maskfile : str
        Name of the mask file.
    """
    from subprocess import check_call
    cmd = [
        "deepdefacer",
        "--input_file",
        in_file,
        "--defaced_output_path",
        out_file,
        "--mask_output_path",
        maskfile,
    ]
    check_call(cmd)
    return out_file


def run_deepdefacer(in_file, out_file):
    """
    Setup and run mridefacer workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    subject_label : str
        Label of subject to operate on (without 'sub-').
    bids_dir : str
        Path to BIDS root directory.
    """
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    maskfile = os.path.splitext(in_file)[0]
    while os.path.splitext(maskfile)[1]:
        maskfile = os.path.splitext(maskfile)[0]
    maskfile += "_space-native_defacemask-deepdefacer.nii.gz"

    deepdefacer = pe.Node(
        Function(
            input_names=["in_file", "out_file", "maskfile"],
            output_names=["out_file"],
            function=deepdefacer_cmd,
        ),
        name="deepdefacer",
    )
    deepdefacer.inputs.in_file = in_file
    deepdefacer.inputs.out_file = out_file
    deepdefacer.inputs.maskfile = maskfile
    results = deepdefacer.run()
    out_file = results.outputs.out_file
    return out_file


def run_t2w_deface(in_file, t1w_deface_mask, out_file):
    """
    Setup and run t2w defacing workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    t1w_deface_mask : str
        Path to the defaced T1w image that will be used
        as defacing mask.
    outfile : str
        Name of the defaced file.
    """

    from bidsonym.utils import deface_t2w
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    flirtnode = pe.Node(
        FLIRT(cost_func="mutualinfo", output_type="NIFTI_GZ"), name="flirtnode"
    )
    deface_t2w = pe.Node(
        Function(
            input_names=["in_file", "warped_mask", "out_file"],
            output_names=["out_file"],
            function=deface_t2w,
        ),
        name="deface_t2w",
    )
    deface_wf.connect(
        [
            (inputnode, flirtnode, [("in_file", "reference")]),
            (inputnode, deface_t2w, [("in_file", "in_file")]),
            (flirtnode, deface_t2w, [("out_file", "warped_mask")]),
        ]
    )
    inputnode.inputs.in_file = in_file
    flirtnode.inputs.in_file = t1w_deface_mask
    deface_t2w.inputs.out_file = out_file
    deface_wf.run()
    return out_file
