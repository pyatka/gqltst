import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gqltst",
    version="0.0.8",
    author="Andrey Mazur",
    author_email="pyatka.aag@gmail.com",
    description="""Framework for automatic GraphQL testing. The framework takes url of your GraphQL endpoint,
                    builds schema and generates http queries for testing.""",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pyatka/gqltst",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
