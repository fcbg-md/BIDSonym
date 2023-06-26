import shutil
import tempfile
import os

import docker
import json

client = docker.from_env()


def run_container(image, arguments, volumes):
    print(f"Running {image}")
    container = client.containers.run(
        image=image,
        command=arguments,
        volumes=volumes,
        detach=True
    )
    # Wait for the container to finish
    exit_code = container.wait()
    logs = container.logs().decode("utf-8")
    return(exit_code, logs)


def build_container(dockerfile_path, image_tag):
    print(f"Building {image_tag}")
    docker_client = docker.APIClient()
    generator = docker_client.build(path=dockerfile_path, tag=image_tag, rm=True, decode=True)
    while True:
        try:
            output = generator.__next__()
            if 'stream' in output:
               print(output['stream'].strip('\n'))
            if 'errorDetail' in output:
                raise ValueError(output['errorDetail'])
        except StopIteration:
            print("Docker image build complete.")
            break
        except ValueError:
            print("Error parsing output from docker image build: %s" % output)

image_tag = "bidsonym-test:latest"
build = True
if build:
    dockerfile_path =  os.path.dirname(os.path.abspath(__file__))
    build_container(dockerfile_path, image_tag)

# docker run -v C:\Users\victor.ferat\Documents\DATA\ds004590:/input test --participant_label 01 --deid pydeface --deface_t2w --brainextraction nobrainer /input group
arguments = []
for deid in ['pydeface', 'mri_deface', 'quickshear', 'mridefacer', 'deepdefacer']:
    argument = ['--participant_label', '01', '--deid', deid, '--deface_t2w', '--brainextraction', 'nobrainer', '/input', 'group']
    arguments.append(argument)

source_folder = r"C:\Users\victor.ferat\Documents\DATA\ds004590"
for argument in arguments:
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_bids = os.path.join(temp_dir, "bids")
    print("Temporary directory:", temp_bids)
    # Copy the source folder to the destination folder
    shutil.copytree(source_folder, temp_bids, ignore=shutil.ignore_patterns('.git*', '.datalad*'))
    volumes={
            temp_bids: {
                'bind': "/input",
                'mode': 'rw'
            }
        }
    # Run container
    exit_code, logs = run_container(image_tag, volumes=volumes, arguments=argument)
    print (argument, exit_code, logs)
    os.remove(temp_dir)