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
    nodeid_layout =  BIDSLayout(nodeid_path)

    source_path = file.path
    nodeied_file_path = nodeid_layout.build_path(file.entities)
    
    move_file(source_path, nodeied_file_path)
    return(nodeied_file_path)


def check_meta_data(bids_dir, subject_label, prob_fields=None):
    """
    Extract meta-data from image headers and json files and
    subsequently evaluate values based on default keys or
    user specified keys. Outputs are csv files containing
    DataFrames with keys, values and markers concerning values.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.
    subject_label : str
        Label of subject to be checked (without 'sub-').
    prob_fields : list, optional
        List of meta-data keys ('str') that should be evaluated.
    """

    list_subject_image_files = glob(os.path.join(bids_dir, 'sub-' + subject_label, '**/*.nii.gz'), recursive=True)
    list_task_meta_files = glob(os.path.join(bids_dir, '*json'))
    list_sub_meta_files = glob(os.path.join(bids_dir, 'sub-' + subject_label, '**/*.json'), recursive=True)
    list_meta_files = list_task_meta_files + list_sub_meta_files

    for subject_image_file in list_subject_image_files:

        header = nib.load(subject_image_file).header
        keys = []
        dat = []

        for key, data in zip(header.keys(), header.values()):
            keys.append(key)
            dat.append(data)
        header_df = pd.DataFrame({'header_data_field': keys, 'data': dat, 'problematic': 'no'})

        if prob_fields:
            prob_fields = prob_fields + ['descrip']
        else:
            prob_fields = ['descrip']

        for index, row in header_df.iterrows():
            if any(i.lower() in row['header_data_field'] for i in prob_fields):
                row['problematic'] = 'maybe'
            else:
                row['problematic'] = 'no'

        header_df.to_csv(os.path.join(bids_dir, 'sourcedata/bidsonym',
                                      'sub-%s' % subject_label,
                                      subject_image_file[subject_image_file.rfind('/') +
                                                         1:subject_image_file.rfind('.nii.gz')] +
                                      '_desc-headerinfo.csv'),
                         index=False)

    logger.info('the following meta-data files will be checked:')
    logger.info(*list_meta_files, sep='\n')

    for meta_file in list_meta_files:

        with open(meta_file, 'r') as json_file:
            meta_data = json.load(json_file)
            keys = []
            info = []
            for key, inf in zip(meta_data.keys(), meta_data.values()):
                keys.append(key)
                info.append(inf)
            json_df = pd.DataFrame({'meta_data_field': keys, 'information': info, 'problematic': 'no'})

        list_general_prob_fields = ['AcquisitionTime', 'InstitutionAddress', 'InstitutionName',
                                    'InstitutionalDepartmentName', 'ProcedureStepDescription', 'ProtocolName',
                                    'PulseSequenceDetails', 'SeriesDescription', 'global']

        if prob_fields:
            prob_fields = prob_fields + list_general_prob_fields
        else:
            prob_fields = list_general_prob_fields

        for index, row in json_df.iterrows():
            if any(i in row['meta_data_field'] for i in prob_fields):
                row['problematic'] = 'maybe'
            else:
                row['problematic'] = 'no'

        json_df.to_csv(os.path.join(bids_dir, 'sourcedata/bidsonym', 'sub-%s' % subject_label,
                                    meta_file[meta_file.rfind('/') +
                                              1:meta_file.rfind('.json')] +
                                    '_desc-jsoninfo.csv'),
                       index=False)


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
    layout = BIDSLayout(bids_dir)
    # no deid layout
    nodeid_path = os.path.join(bids_dir, "sourcedata", "bidsonym")
    nodeid_layout =  BIDSLayout(nodeid_path)

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
            nodeied_file_path = nodeid_layout.build_path(file.entities)
            move_file(file_path, nodeied_file_path)
            with open(file_path, 'w') as json_output_file:
                json.dump(meta_data, json_output_file, indent=4)


def rename_non_deid(bids_dir, subject_label):
    """
    Rename orginal non-defaced images and meta-data json files
    to add respective identifier ('desc-nondeid').

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.
    subject_label : str
        Label of subject to be renamed (without 'sub-').
    """

    list_meta_files = [fn for fn in glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-'
                       + subject_label, '*json')) if not os.path.basename(fn).endswith('desc-nondeid.json')]
    list_images_files = [fn for fn in glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-'
                         + subject_label, '*nii.gz')) if not os.path.basename(fn).endswith('desc-nondeid.nii.gz')]

    for meta_data_file in list_meta_files:
        meta_deid = meta_data_file[meta_data_file.rfind('/') +
                                   1:meta_data_file.rfind('.json')] + '_desc-nondeid.json'
        os.rename(meta_data_file, os.path.join(bids_dir, 'sourcedata/bidsonym/sub-' + subject_label, meta_deid))

    for image_file in list_images_files:
        image_deid = image_file[image_file.rfind('/') +
                                1:image_file.rfind('.nii.gz')] + '_desc-nondeid.nii.gz'
        os.rename(image_file, os.path.join(bids_dir, 'sourcedata/bidsonym/sub-' + subject_label, image_deid))


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


def validate_input_dir(exec_env, bids_dir, participant_label):
    """
    Validate BIDS directory and structure via the BIDS-validator.
    Functionality copied from fmriprep.

    Parameters
    ----------
    exec_env : str
        Environment BIDSonym is run in.
    bids_dir : str
        Path to BIDS root directory.
    participant_label: str
        Label(s) of subject to be checked (without 'sub-').
    """

    import tempfile
    import subprocess
    validator_config_dict = {
        "ignore": [
            "EVENTS_COLUMN_ONSET",
            "EVENTS_COLUMN_DURATION",
            "TSV_EQUAL_ROWS",
            "TSV_EMPTY_CELL",
            "TSV_IMPROPER_NA",
            "VOLUME_COUNT_MISMATCH",
            "BVAL_MULTIPLE_ROWS",
            "BVEC_NUMBER_ROWS",
            "DWI_MISSING_BVAL",
            "INCONSISTENT_SUBJECTS",
            "INCONSISTENT_PARAMETERS",
            "BVEC_ROW_LENGTH",
            "B_FILE",
            "PARTICIPANT_ID_COLUMN",
            "PARTICIPANT_ID_MISMATCH",
            "TASK_NAME_MUST_DEFINE",
            "PHENOTYPE_SUBJECTS_MISSING",
            "STIMULUS_FILE_MISSING",
            "DWI_MISSING_BVEC",
            "EVENTS_TSV_MISSING",
            "TSV_IMPROPER_NA",
            "ACQTIME_FMT",
            "Participants age 89 or higher",
            "DATASET_DESCRIPTION_JSON_MISSING",
            "FILENAME_COLUMN",
            "WRONG_NEW_LINE",
            "MISSING_TSV_COLUMN_CHANNELS",
            "MISSING_TSV_COLUMN_IEEG_CHANNELS",
            "MISSING_TSV_COLUMN_IEEG_ELECTRODES",
            "UNUSED_STIMULUS",
            "CHANNELS_COLUMN_SFREQ",
            "CHANNELS_COLUMN_LOWCUT",
            "CHANNELS_COLUMN_HIGHCUT",
            "CHANNELS_COLUMN_NOTCH",
            "CUSTOM_COLUMN_WITHOUT_DESCRIPTION",
            "ACQTIME_FMT",
            "SUSPICIOUSLY_LONG_EVENT_DESIGN",
            "SUSPICIOUSLY_SHORT_EVENT_DESIGN",
            "MALFORMED_BVEC",
            "MALFORMED_BVAL",
            "MISSING_TSV_COLUMN_EEG_ELECTRODES",
            "MISSING_SESSION"
        ],
        "error": ["NO_T1W"],
        "ignoredFiles": ['/dataset_description.json', '/participants.tsv']
    }
    # Limit validation only to data from requested participants
    if participant_label:
        all_subs = set([s.name[4:] for s in bids_dir.glob('sub-*')])
        selected_subs = set([s[4:] if s.startswith('sub-') else s
                             for s in participant_label])
        bad_labels = selected_subs.difference(all_subs)
        if bad_labels:
            error_msg = 'Data for requested participant(s) label(s) not found. Could ' \
                        'not find data for participant(s): %s. Please verify the requested ' \
                        'participant labels.'
            if exec_env == 'docker':
                error_msg += ' This error can be caused by the input data not being ' \
                             'accessible inside the docker container. Please make sure all ' \
                             'volumes are mounted properly (see https://docs.docker.com/' \
                             'engine/reference/commandline/run/#mount-volume--v---read-only)'
            if exec_env == 'singularity':
                error_msg += ' This error can be caused by the input data not being ' \
                             'accessible inside the singularity container. Please make sure ' \
                             'all paths are mapped properly (see https://www.sylabs.io/' \
                             'guides/3.0/user-guide/bind_paths_and_mounts.html)'
            raise RuntimeError(error_msg % ','.join(bad_labels))

        ignored_subs = all_subs.difference(selected_subs)
        if ignored_subs:
            for sub in ignored_subs:
                validator_config_dict["ignoredFiles"].append("/sub-%s/**" % sub)
    with tempfile.NamedTemporaryFile('w+') as temp:
        temp.write(json.dumps(validator_config_dict))
        temp.flush()
        try:
            subprocess.check_call(['bids-validator', bids_dir, '-c', temp.name])
        except FileNotFoundError:
            raise FileNotFoundError("bids-validator does not appear to be installed.")


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


def clean_up_files(bids_dir, subject_label, session=None):
    """
    Restructure BIDSonym outcomes following BIDS conventions.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS root directory.
    subject_label : str
        Label of subject to move (without 'sub-').
    session : str, optional
        If multiple sessions exist, create session specific
        structure.
    """

    if session is not None:
        out_path_images = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s/ses-%s/images"
                                       % (subject_label, session))
        out_path_info = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s/ses-%s/meta_data_info"
                                     % (subject_label, session))
        list_imaging_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label,
                                               'sub-' + subject_label + '_ses-' + session + '*.nii.gz'))
        list_graphics = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label,
                                          'sub-' + subject_label + '_ses-' + session + '*.png'))
        list_gifs = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label,
                                      'sub-' + subject_label + '_ses-' + session + '*.gif'))
        list_info_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label,
                                            'sub-' + subject_label + '_ses-' + session + '*.csv'))
        list_meta_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label,
                                            'sub-' + subject_label + '_ses-' + session + '*.json'))
    else:
        out_path_images = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s/images" % subject_label)
        out_path_info = os.path.join(bids_dir, "sourcedata/bidsonym/sub-%s/meta_data_info" % subject_label)
        list_imaging_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label, '*.nii.gz'))
        list_graphics = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label, '*.png'))
        list_gifs = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label, '*.gif'))
        list_info_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label, '*.csv'))
        list_meta_files = glob(os.path.join(bids_dir, 'sourcedata/bidsonym/sub-%s' % subject_label, '*.json'))

    if os.path.isdir(out_path_images) is False:
        os.makedirs(out_path_images)

    if os.path.isdir(out_path_info) is False:
        os.makedirs(out_path_info)

    images = list_imaging_files + list_graphics + list_gifs

    for image_file in images:
        file_out = image_file[image_file.rfind('/') + 1:]
        move(image_file, os.path.join(out_path_images, file_out))

    for info_file in list_info_files+list_meta_files:
        file_out = info_file[info_file.rfind('/') + 1:]
        move(info_file, os.path.join(out_path_info, file_out))
