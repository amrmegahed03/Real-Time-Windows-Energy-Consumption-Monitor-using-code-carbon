from setuptools import setup, find_packages

setup(
    name='real-time-energy-monitor',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'psutil',
        'requests',
        'pynvml',
        'numpy',
        'pandas',
        'matplotlib',
        'seaborn',
        'scikit-learn',
        'scipy',
        # Add additional dependencies if required
    ],
    author='Amr Megahed Ahmed',
    description='Real-Time Windows Energy Consumption Monitor using a custom fork of CodeCarbon',
    url='https://github.com/amrmegahed03/Real-Time-Windows-Energy-Consumption-Monitor-using-code-carbon',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
    python_requires='>=3.6',
)