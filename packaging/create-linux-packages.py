#!/usr/bin/env python3

"""
Create Ubuntu and Fedora packages in out/.

Usage:
create-linux-packages.py <release-version>
"""

import sys
from shutil import rmtree
from subprocess import run
from pathlib import Path

THIS_DIRECTORY = Path(__file__).absolute().parent


def build_package(builder_image, package_type, version, out_dir, dependencies):
    """
    Build a deb or RPM package using a fpm-within-docker Docker image.

    :param package_type str: "rpm" or "deb".
    :param version str: The package version.
    :param out_dir Path: Directory where package will be output.
    :param dependencies list: package names the resulting package should depend
        on.
    """
    run([
        "docker", "run", "--rm", "-e", "PACKAGE_VERSION=" + version,
        "-e", "PACKAGE_TYPE=" + package_type,
        "-v", "{}:/build-inside:rw".format(THIS_DIRECTORY),
        "-v", "{}:/source:rw".format(THIS_DIRECTORY.parent),
        "-v", str(out_dir) + ":/out", "-w", "/build-inside", builder_image,
        "/build-inside/build-package.sh", *dependencies
    ],
        check=True)


def test_package(distro_image, package_directory, install_command):
    """
    Test a package can be installed and run.

    :param distro_image str: The Docker image to use to test the package.
    :param package_directory Path: local directory where the package can be
        found.
    :param install_command str: "deb" or "rpm".
    """
    if install_command == "deb":
        install = (
            "apt-get -q update && "
            "apt-get -q -y --no-install-recommends install gdebi-core && "
            "gdebi -n /packages/*.deb"
        )
    elif install_command == "rpm":
        install = "dnf -y install /packages/*.rpm"

    run([
        "docker", "run", "--rm",
        "-e", "LC_ALL=C.UTF-8",
        "-e", "LANG=C.UTF-8",
        "-v", "{}:/packages:ro".format(package_directory), distro_image, "sh", "-c",
        install + " && kubernaut --help"
    ],
        check=True)


def main(version):
    out = THIS_DIRECTORY / "out"

    if out.exists():
        rmtree(str(out))
    out.mkdir()

    for ubuntu_distro in ["xenial", "yakkety", "zesty"]:
        distro_out = out / ubuntu_distro
        distro_out.mkdir()
        image = "alanfranz/fpm-within-docker:ubuntu-{}".format(ubuntu_distro)

        build_package(
            image, "deb", version, distro_out, ["python3"]
        )
        test_package("ubuntu:" + ubuntu_distro, distro_out, "deb")

    for fedora_distro in ["25", "26"]:
        distro_out = out / ("fedora-" + fedora_distro)
        distro_out.mkdir()
        build_package(
            "alanfranz/fpm-within-docker:fedora-{}".format(fedora_distro), "rpm",
            version, distro_out, ["python3"]
        )
        test_package("fedora:" + fedora_distro, distro_out, "rpm")


if __name__ == '__main__':
    main(sys.argv[1])
