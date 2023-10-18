from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in dhl_integration/__init__.py
from dhl_integration import __version__ as version

setup(
	name="dhl_integration",
	version=version,
	description="Frappe app to integrate ERPNext with DHL API",
	author="Othermo GmbH",
	author_email="malisa.aisenyi@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
