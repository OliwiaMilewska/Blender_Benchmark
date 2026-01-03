from setuptools import setup, find_packages

setup(
    name="blender_benchmark",
    version="1.0.0",
    description="Python script to test rendering engines in Blender",
    author="Oliwia Milewska",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "pynvml>=11.5.0",
        "scikit-image>=0.21.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.10.0",
    ],
    entry_points={
        "console_scripts": [
            "blender-benchmark=blender_benchmark.cli:main",
        ],
    },
)
