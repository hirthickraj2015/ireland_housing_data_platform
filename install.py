"""
Running this script imports all needed packages for the project, where these packages have been defined in the config
file
"""
import os

# -- Define Variables ------------------------------------------------------------------------------------------------ #

required_packages = ['pandas', 'numpy', 'dask', 'tableau-api-lib', 'tableauhyperapi']


# -- Define Functions ------------------------------------------------------------------------------------------------ #

def install_python_packages(packages):

    for package in packages:

        if not isinstance(package, str):
            try:
                os.system('cmd /c "pip install {}"'.format(str(package)))

            except:
                print("Failed to install package because package given is not in string format.")

        if isinstance(package, str):
            try:
                os.system('cmd /c "pip install {}"'.format(package))

            except:
                print("Failed to install {} package.".format(package))

    print("Installation of required packages is completed.")


# -- Script --------------------------------------------------------------------------------------------------------- #

install_python_packages(required_packages)

print('Script completed.')
