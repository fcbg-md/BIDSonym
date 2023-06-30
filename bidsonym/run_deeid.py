import argparse
import os
from pathlib import Path
from .defacing_algorithms import (
    run_pydeface,
    run_mri_deface,
    run_mridefacer,
    run_quickshear,
    run_deepdefacer,
    run_t2w_deface,
)
from .utils import (
    copy_no_deid,
    del_meta_data,
    run_brain_extraction_nb,
    run_brain_extraction_bet,
)

from .reports import nifti_to_gif, plot_overlay

from bids import BIDSLayout

from ._logs import logger, verbose
from ._checks import _check_verbose


@verbose
def run_deeid(
    bids_dir,
    analysis_level,
    participant_label,
    deid,
    del_meta,
    brainextraction,
    bet_frac,
    deface_t2w=True,
    skip_bids_validation=False,
    exec_env="local",
    verbose=None,
):
    verbose = _check_verbose(verbose)
    subjects_to_analyze = []
    # Check brainextraction
    if brainextraction == "bet":
        if bet_frac is None:
            raise ValueError(
                "If you want to use BET for pre-defacing brain extraction,"
                "please provide a Frac value. For example: --bet_frac 0.5"
            )
    if brainextraction is None:
        raise Exception(
            "For post defacing quality it is required to run a form of brainextraction"
            "on the non-deindentified data. Thus please either indicate bet "
            "(--brainextration bet) or nobrainer (--brainextraction nobrainer)."
        )
    # Check subjects_to_analyze
    if analysis_level == "participant" and not participant_label:
        raise ValueError("No participant label indicated. Please do so.")

    if analysis_level == "group" and participant_label:
        raise ValueError("Cannot set participant_label for group level analysis.")

    # Check skip_bids_validation
    if skip_bids_validation:
        logger.info("Input data will not be checked for BIDS compliance.")
    else:
        logger.info("Making sure the input data is BIDS compliant")

    layout = BIDSLayout(bids_dir, validate=not skip_bids_validation)
    if participant_label:
        missing_participants = []
        for participant in subjects_to_analyze:
            if participant not in layout.get_subjects():
                missing_participants.append(participant)
        if len(missing_participants) > 0:
            raise ValueError(
                "The participant(s) %s are not present in the BIDS dataset, please check again."
                % missing_participants
            )
        else:
            subjects_to_analyze = participant_label
    else:
        subjects_to_analyze = layout.get(return_type="id", target="subject")

    logger.info(f"subjects_to_analyze {subjects_to_analyze}")
    # Analyze each subject
    for subject_label in subjects_to_analyze:
        logger.info("Processing participant %s" % subject_label)
        if del_meta:
            del_meta_data(bids_dir, subject_label, del_meta)
        list_t1w = layout.get(subject=subject_label, extension="nii.gz", suffix="T1w")
        # Process T1 files.
        for t1w in list_t1w:
            # t1w is a pybids File object
            T1_file = t1w.path
            logger.info("Processing T1w image %s" % t1w.relpath)
            # Create brainmask
            if brainextraction == "bet":
                brainmask = run_brain_extraction_bet(T1_file, bet_frac[0], subject_label, bids_dir)
            elif brainextraction == "nobrainer":
                brainmask = run_brain_extraction_nb(T1_file, subject_label, bids_dir)

            source_t1w = copy_no_deid(bids_dir, t1w)
            # Delete metadata

            # Deface source_t1w and save it as T1_file (=defaced_t1)
            if deid == "pydeface":
                defaced_t1 = run_pydeface(source_t1w, T1_file)
            elif deid == "mri_deface":
                 defaced_t1 = run_mri_deface(source_t1w, T1_file)
            elif deid == "quickshear":
                 defaced_t1 = run_quickshear(source_t1w, T1_file)
            elif deid == "mridefacer":
                 defaced_t1 = run_mridefacer(source_t1w, T1_file)
            elif deid == "deepdefacer":
                 defaced_t1 = run_deepdefacer(source_t1w, subject_label, bids_dir)
            # Create plots
            T1_overlay = plot_overlay(brainmask, defaced_t1)
            T1_gif = nifti_to_gif(defaced_t1)

            # Process T2 files.
            if deface_t2w:
                T2_entities = t1w.entities.copy()
                T2_entities["suffix"] = "T2w"
                t2w = layout.get(**T2_entities)
                if len(t2w) == 0:
                    logger.warn(
                        "You indicated that a T2w image should be defaced as well."
                        "However, no T2w image exists for T1 image  %s." % source_t1w
                    )
                else:
                    t2w = t2w[0]
                    T2_file = t2w.path
                    logger.info("Processing T2w image %s" % T2_file)
                    if brainextraction == "bet":
                        run_brain_extraction_bet(
                            T2_file, bet_frac[0], subject_label, bids_dir
                        )
                    elif brainextraction == "nobrainer":
                        run_brain_extraction_nb(T2_file, subject_label, bids_dir)

                    source_t2w = copy_no_deid(bids_dir, T2_file)
                    # Deface source_t2w and save it as T2_file (=defaced_t2)
                    defaced_t2 = run_t2w_deface(source_t2w, defaced_t1, T2_file)
                    T2_overlay = plot_overlay(brainmask, defaced_t2)
                    T2_gif = nifti_to_gif(defaced_t2)
                    # TODO: move files


def get_parser():
    __version__ = open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "_version.py")
    ).read()

    parser = argparse.ArgumentParser(
        description="a BIDS app for de-identification of neuroimaging data"
    )
    parser.add_argument(
        "bids_dir",
        action="store",
        type=Path,
        help="The directory with the input dataset "
        "formatted according to the BIDS standard.",
    )

    parser.add_argument(
        "analysis_level",
        help="Level of the analysis that will be performed. "
        "Multiple participant level analyses can be run independently "
        "(in parallel) using the same output_dir.",
        choices=["participant", "group"],
    )
    parser.add_argument(
        "--participant_label",
        help="The label(s) of the participant(s) that should be analyzed. "
        "The label corresponds to sub-<participant_label> from the BIDS spec "
        '(so it does not include "sub-"). If this parameter is not '
        "provided all subjects should be analyzed. Multiple "
        "participants can be specified with a space separated list.",
        nargs="+",
    )
    parser.add_argument(
        "--deid",
        help="Approach to use for de-identifictation.",
        choices=["pydeface", "mri_deface", "quickshear", "mridefacer", "deepdefacer"],
    )
    parser.add_argument(
        "--deface_t2w",
        action="store_true",
        default=True,
        help="Deface T2w images by using defaced T1w image as deface-mask.",
    )
    parser.add_argument(
        "--del_meta",
        help="Indicate if and which information from the .json meta-data files should be deleted. \
                        If so, the original .json files will be copied to sourcedata/",
        nargs="+",
    )
    parser.add_argument(
        "--brainextraction",
        help="What algorithm should be used for pre-defacing brain extraction \
                        (outputs will be used in quality control).",
        choices=["bet", "nobrainer"],
    )
    parser.add_argument(
        "--bet_frac",
        help="In case BET is used for pre-defacing brain extraction, provide a Frac value.",
        nargs=1,
    )
    parser.add_argument(
        "--skip_bids_validation",
        default=False,
        help="Assume the input dataset is BIDS compliant and skip the validation \
                             (default: False).",
        action="store_true",
    )
    parser.add_argument(
        "--verbose",
        default=None,
        help="Set verbose level.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="BIDS-App version {}".format(__version__),
    )
    return parser


def main():
    # special variable set in the container
    if os.getenv("IS_DOCKER"):
        exec_env = "singularity"
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists() and "docker" in cgroup.read_text():
            exec_env = "docker"
    else:
        exec_env = "local"

    args = get_parser().parse_args()
    run_deeid(
        bids_dir=args.bids_dir,
        analysis_level=args.analysis_level,
        participant_label=args.participant_label,
        deid=args.deid,
        deface_t2w=args.deface_t2w,
        del_meta=args.del_meta,
        brainextraction=args.brainextraction,
        bet_frac=args.bet_frac,
        skip_bids_validation=args.skip_bids_validation,
        exec_env=exec_env,
        verbose=args.verbose,
    )
