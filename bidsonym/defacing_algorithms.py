import os

import nipype.pipeline.engine as pe
from nipype import Function
from nipype.interfaces import utility as niu
from nipype.interfaces.fsl import BET, FLIRT
from nipype.interfaces.quickshear import Quickshear


def pydeface_cmd(image, outfile):
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
        image,
        "--out",
        outfile,
        "--force",
    ]
    check_call(cmd)
    return


def run_pydeface(image, outfile):
    """
    Setup and run pydeface workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """

    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    pydeface = pe.Node(
        Function(
            input_names=["image", "outfile"],
            output_names=["outfile"],
            function=pydeface_cmd,
        ),
        name="pydeface",
    )
    deface_wf.connect([(inputnode, pydeface, [("in_file", "image")])])
    inputnode.inputs.in_file = image
    pydeface.inputs.outfile = outfile
    deface_wf.run()
    return outfile


def mri_deface_cmd(image, outfile):
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
        image,
        "/home/bm/bidsonym/fs_data/talairach_mixed_with_skull.gca",
        "/home/bm/bidsonym/fs_data/face.gca",
        outfile,
    ]
    check_call(cmd)
    return


def run_mri_deface(image, outfile):
    """
    Setup and run mri_deface workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """

    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    mri_deface = pe.Node(
        Function(
            input_names=["image", "outfile"],
            output_names=["outfile"],
            function=mri_deface_cmd,
        ),
        name="mri_deface",
    )
    deface_wf.connect([(inputnode, mri_deface, [("in_file", "image")])])
    inputnode.inputs.in_file = image
    mri_deface.inputs.outfile = outfile
    deface_wf.run()
    return outfile


def run_quickshear(image, outfile):
    """
    Setup and run quickshear workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """

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
    inputnode.inputs.in_file = image
    quickshear.inputs.out_file = outfile
    deface_wf.run()
    return outfile


def mridefacer_cmd(image, outfile):
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

    outdir = outfile[: outfile.rfind("/")]

    cmd = ["/mridefacer/mridefacer", "--apply", image, "--outdir", outdir]
    check_call(cmd)
    return


def run_mridefacer(image, outfile):
    """
    Setup and mridefacer workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of the defaced file.
    """
    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    mridefacer = pe.Node(
        Function(
            input_names=["image", "T1_file"],
            output_names=["outfile"],
            function=mridefacer_cmd,
        ),
        name="mridefacer",
    )
    deface_wf.connect([(inputnode, mridefacer, [("in_file", "image")])])
    inputnode.inputs.in_file = image
    mridefacer.inputs.T1_file = outfile
    deface_wf.run()
    return image


def deepdefacer_cmd(image, output, maskfile):
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
        image,
        "--defaced_output_path",
        output,
        "--mask_output_path",
        maskfile,
    ]
    check_call(cmd)
    return output


def run_deepdefacer(image, output):
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
    maskfile = os.path.splitext(image)[0]
    while os.path.splitext(maskfile)[1]:
        maskfile = os.path.splitext(maskfile)[0]
    maskfile += "_space-native_defacemask-deepdefacer.nii.gz"
    deepdefacer = pe.Node(
        Function(
            input_names=["image", "subject_label", "bids_dir"],
            output_names=["outfile"],
            function=deepdefacer_cmd,
        ),
        name="deepdefacer",
    )
    deepdefacer.inputs.image = image
    deepdefacer.inputs.output = output
    deepdefacer.inputs.maskfile = maskfile
    deepdefacer.run()
    return output


def run_t2w_deface(image, t1w_deface_mask, outfile):
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

    deface_wf = pe.Workflow("deface_wf")
    inputnode = pe.Node(niu.IdentityInterface(["in_file"]), name="inputnode")
    flirtnode = pe.Node(
        FLIRT(cost_func="mutualinfo", output_type="NIFTI_GZ"), name="flirtnode"
    )
    deface_t2w = pe.Node(
        Function(
            input_names=["image", "warped_mask", "outfile"],
            output_names=["outfile"],
            function=deface_t2w,
        ),
        name="deface_t2w",
    )
    deface_wf.connect(
        [
            (inputnode, flirtnode, [("in_file", "reference")]),
            (inputnode, deface_t2w, [("in_file", "image")]),
            (flirtnode, deface_t2w, [("out_file", "warped_mask")]),
        ]
    )
    inputnode.inputs.in_file = image
    flirtnode.inputs.in_file = t1w_deface_mask
    deface_t2w.inputs.outfile = outfile
    deface_wf.run()
    return outfile
