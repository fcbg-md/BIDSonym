#!/bin/sh

#Generate Dockerfile.
# TODO: fix deepdefacer dependencies and remove --env SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
set -e

generate_docker() {
  docker run --rm repronim/neurodocker:0.9.5 generate docker \
             --base-image bids/base_validator \
             --yes \
             --pkg-manager apt \
             --install git num-utils gcc g++ curl build-essential nano\
             --run-bash "git config --global --add user.name test" \
             --run-bash "git config --global --add user.email bob@example.com"\
             --fsl version=6.0.6.4 method=binaries \
             --run-bash "git clone https://github.com/mih/mridefacer" \
             --env MRIDEFACER_DATA_DIR=/mridefacer/data \
             --run-bash "mkdir /home/mri-deface-detector && cd /home/mri-deface-detector && npm install sharp --unsafe-perm && npm install -g mri-deface-detector --unsafe-perm && cd ~" \
             --env IS_DOCKER=1 \
             --env SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True \
             --miniconda \
                version=latest \
                env_name=bidsonym \
                env_exists=false\
                conda_install="python=3.10" \
                pip_install="datalad-osf" \
             --run-bash "apt-get update && apt-get install -y datalad" \
             --run-bash "source activate /opt/miniconda-latest/envs/bidsonym && mkdir -p /opt/nobrainer/models && cd /opt/nobrainer/models && datalad clone https://github.com/neuronets/trained-models && cd trained-models && git-annex enableremote osf-storage && datalad get -s osf-storage ." \
             --copy . /home/bm \
             --run-bash "chmod a+x /home/bm/bidsonym/fs_data/mri_deface" \
             --run-bash "source activate /opt/miniconda-latest/envs/bidsonym && cd /home/bm && pip install -r requirements.txt && pip install -e ." \
             --workdir '/tmp/' \
             --run-bash 'echo "#!/bin/bash" >> /entrypoint.sh' \
             --run-bash 'echo "source activate bidsonym" >> /entrypoint.sh' \
             --run-bash 'echo "bidsonym \"\$@\"" >> /entrypoint.sh'\
             --run-bash 'chmod +x /entrypoint.sh'\
             --env NIPYPE_NO_ET=1 \
             --entrypoint "/entrypoint.sh"
}

# generate files
generate_docker > Dockerfile

# check if images should be build locally or not
if [ '$1' = 'local' ]; then
    echo "docker image will be build locally"
    # build image using the saved files
    docker build -t bidsonym:local .
else
  echo "Image(s) won't be build locally."
fi
