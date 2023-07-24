import docker

from .. import __version__

client = docker.from_env()
image = 'bidsonym_tests'


def run_container(image, arguments, volumes):
    print(f"Running {image}")
    container = client.containers.run(
        image=image, command=arguments, volumes=volumes, detach=True
    )
    # Wait for the container to finish
    exit_code = container.wait()
    logs = container.logs().decode("utf-8")
    return (exit_code, logs)


def test_version():
    status, logs = run_container(image, ["--version"], None)
    assert status['StatusCode'] == 0
    assert __version__ in logs
