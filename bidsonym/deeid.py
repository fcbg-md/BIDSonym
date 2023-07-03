import os

from bids import BIDSLayout

from ._checks import _check_verbose
from ._logs import logger, verbose
from .brainextraction import run_brain_extraction_bet, run_brain_extraction_nb
from .defacing_algorithms import (
    run_deepdefacer,
    run_mri_deface,
    run_mridefacer,
    run_pydeface,
    run_quickshear,
    run_t2w_deface,
)
from .reports import nifti_to_gif, plot_overlay
from .utils import copy_no_deid, del_meta_data


@verbose
def deeid(
    bids_dir,
    analysis_level,
    participant_label,
    deid,
    del_meta,
    brainextraction,
    bet_frac,
    deface_t2w=True,
    skip_bids_validation=False,
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
            "For post defacing quality it is required to run a "
            "form of brainextraction on the non-deindentified data."
            "Thus please either indicate bet (--brainextration bet) "
            "or nobrainer (--brainextraction nobrainer)."
        )
    # Check subjects_to_analyze
    if analysis_level == "participant" and not participant_label:
        raise ValueError("No participant label indicated. Please do so.")

    if analysis_level == "group" and participant_label:
        raise ValueError(
            "Cannot set participant_label for group level analysis."
        )

    # Check skip_bids_validation
    if skip_bids_validation:
        logger.info("Input data will not be checked for BIDS compliance.")
    else:
        logger.info("Making sure the input data is BIDS compliant")

    # Check participant_label
    layout = BIDSLayout(
        bids_dir, validate=not skip_bids_validation, derivatives=False
    )
    if participant_label:
        missing_participants = []
        for participant in subjects_to_analyze:
            if participant not in layout.get_subjects():
                missing_participants.append(participant)
        if len(missing_participants) > 0:
            raise ValueError(
                "The participant(s) %s are not present in the BIDS dataset, "
                "please check again." % missing_participants
            )
        else:
            subjects_to_analyze = participant_label
    else:
        subjects_to_analyze = layout.get(return_type="id", target="subject")

    logger.info(f"subjects_to_analyze {subjects_to_analyze}")
    # Analyze each subject
    for subject_label in subjects_to_analyze:
        logger.info("Processing participant %s" % subject_label)
        # Delete meta data
        if del_meta:
            del_meta_data(bids_dir, subject_label, del_meta)

        # Process T1 files.
        list_t1w = layout.get(
            subject=subject_label, extension="nii.gz", suffix="T1w"
        )
        for t1w in list_t1w:
            # t1w is a pybids File object
            T1_file = t1w.path
            logger.info("Processing T1w image %s" % t1w.relpath)
            source_t1w = copy_no_deid(bids_dir, t1w)

            # Create brainmask
            brainmask_path = os.path.splitext(source_t1w)[0]
            while os.path.splitext(brainmask_path)[1]:
                brainmask_path = os.path.splitext(brainmask_path)[0]
            brainmask_path += "_brainmask.nii.gz"
            logger.info("Extracting brainmask to %s" % brainmask_path)
            if brainextraction == "bet":
                brainmask_t1 = run_brain_extraction_bet(
                    source_t1w, bet_frac[0], brainmask_path
                )
            elif brainextraction == "nobrainer":
                brainmask_t1 = run_brain_extraction_nb(
                    source_t1w, brainmask_path
                )

            # Deface source_t1w and save it as T1_file (=defaced_t1)
            if deid == "pydeface":
                defaced_t1 = run_pydeface(source_t1w, T1_file)
            elif deid == "mri_deface":
                defaced_t1 = run_mri_deface(source_t1w, T1_file)
            elif deid == "quickshear":
                defaced_t1 = run_quickshear(source_t1w, T1_file)
            elif deid == "mridefacer":
                outdir = os.path.dirname(T1_file)
                defaced_t1 = run_mridefacer(source_t1w, outdir)
            elif deid == "deepdefacer":
                defaced_t1 = run_deepdefacer(source_t1w, T1_file)

            # Create plots
            T1_overlay = plot_overlay(brainmask_t1, defaced_t1)
            T1_gif = nifti_to_gif(defaced_t1)

            # Process T2 files.
            if deface_t2w:
                # check if T2w image exists
                T2_entities = t1w.entities.copy()
                T2_entities["suffix"] = "T2w"
                T2_file = layout.build_path(T2_entities)
                if not os.path.isfile(T2_file):
                    logger.warn(
                        "You indicated that a T2w image should be defaced,"
                        f" However, the T2w image {T2_file} doesn't exist "
                        f"for T1 image {T1_file}."
                    )
                else:
                    t2w = layout.get_file(T2_file)
                    source_t2w = copy_no_deid(bids_dir, t2w)
                    logger.info("Processing T2w image %s" % T2_file)
                    # Create brainmask
                    brainmask_path = os.path.splitext(source_t2w)[0]
                    while os.path.splitext(brainmask_path)[1]:
                        brainmask_path = os.path.splitext(brainmask_path)[0]
                    brainmask_path += "_brainmask.nii.gz"
                    if brainextraction == "bet":
                        brainmask_t2 = run_brain_extraction_bet(
                            source_t2w, bet_frac[0], brainmask_path
                        )
                    elif brainextraction == "nobrainer":
                        brainmask_t2 = run_brain_extraction_nb(
                            source_t2w, brainmask_path
                        )

                    # Deface source_t2w and save it as T2_file (=defaced_t2)
                    defaced_t2 = run_t2w_deface(
                        source_t2w, defaced_t1, T2_file
                    )
                    T2_overlay = plot_overlay(brainmask_t2, defaced_t2)
                    T2_gif = nifti_to_gif(defaced_t2)
                    # TODO: move files
