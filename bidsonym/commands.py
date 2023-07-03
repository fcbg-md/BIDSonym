import argparse
from pathlib import Path

from . import __version__
from .deeid import deeid


def get_parser():
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
        choices=[
            "pydeface",
            "mri_deface",
            "quickshear",
            "mridefacer",
            "deepdefacer",
        ],
    )
    parser.add_argument(
        "--deface_t2w",
        action="store_true",
        default=False,
        help="Deface T2w images by using defaced T1w image as deface-mask.",
    )
    parser.add_argument(
        "--del_meta",
        help="Indicate if and which information from the .json meta-data \
            files should be deleted. If so, the original .json files will \
             be copied to sourcedata.",
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
        help="In case BET is used for pre-defacing brain extraction, \
        provide a Frac value.",
        nargs=1,
    )
    parser.add_argument(
        "--skip_bids_validation",
        default=False,
        help="Assume the input dataset is BIDS compliant \
              and skip the validation (default: False).",
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
    args = get_parser().parse_args()
    deeid(
        bids_dir=args.bids_dir,
        analysis_level=args.analysis_level,
        participant_label=args.participant_label,
        deid=args.deid,
        deface_t2w=args.deface_t2w,
        del_meta=args.del_meta,
        brainextraction=args.brainextraction,
        bet_frac=args.bet_frac,
        skip_bids_validation=args.skip_bids_validation,
        verbose=args.verbose,
    )
