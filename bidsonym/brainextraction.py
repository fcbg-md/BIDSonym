import os

import nipype.pipeline.engine as pe
from nipype import Function
from nipype.interfaces.fsl import BET


def brain_extraction_nb(infile, outfile):
    """
    Setup nobrainer brainextraction command.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of thebrainmask.
    """
    from subprocess import check_call

    cmd = [
        "nobrainer",
        "predict",
        "--model=/opt/nobrainer/models/trained-models/neuronets/brainy/0.1.0/weights/brain-extraction-unet-128iso-model.h5",
        "--verbose",
        infile,
        outfile,
    ]
    check_call(cmd)
    return outfile


def run_brain_extraction_nb(infile, outfile):
    """
    Setup and run nobrainer brainextraction workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    outfile : str
        Name of brainmask.
    """
    dir_name = os.path.dirname(outfile)
    os.makedirs(dir_name, exist_ok=True)

    brainextraction = pe.Node(
        Function(
            input_names=["infile", "outfile"],
            output_names=["outfile"],
            function=brain_extraction_nb,
        ),
        name="brainextraction",
    )
    brainextraction.inputs.infile = infile
    brainextraction.inputs.outfile = outfile
    result = brainextraction.run()
    outfile = result.outputs.outfile
    return outfile


def run_brain_extraction_bet(infile, frac, outfile):
    """
    Setup and FSLs brainextraction (BET) workflow.

    Parameters
    ----------
    image : str
        Path to image that should be defaced.
    frac : float
        Fractional intensity threshold (0 - 1).
    outfile : str
        Name of the brainmask.
    """
    dir_name = os.path.dirname(outfile)
    os.makedirs(dir_name, exist_ok=True)

    bet = pe.Node(BET(mask=False), name="bet")
    bet.inputs.in_file = infile
    bet.inputs.out_file = outfile
    bet.inputs.frac = float(frac)
    bet.run()
    result = bet.run()
    outfile = result.outputs.out_file
    return outfile
