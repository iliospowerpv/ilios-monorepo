# iliOS-DocAI #

This is the main code repository for iliOS-DocAI PoC project. Read the guidelines below.

## Setup ###

### Install `poetry`

With your preferred method install `poetry` tool. Please note, that installing `poetry`
with other that **recommended** method (curl) could cause troubles. Using `pip`,
`homebrew` or other similar method could cause `PATH` problems and lead
to errors while setting-up some packages.
See [installation instructions for poetry](https://github.com/python-poetry/poetry#installation).

### Install dependencies

Make sure you have support for Makefile files with `make` command. If not, install it with your package manager.
Then just run:
```sh
make install
```

There are two sets of dependencies, group "chatbot" contains additional packages for chatbot functionality. 
Install them accordingly with a group flag using poetry. They should be included in the requirements.txt file 
for specific Docker container:
1. with chatbot dependencies: FAST Api service src/deployment/fast_api/Dockerfile, requirements.txt, Makefile: export_requirements_fastapi:
2. without chatbot dependencies: src/deployment/cloud_run_job/key_value_extraction/Dockerfile, requirements_key_extraction.txt, Makefile: export_requirements_key_extraction

```sh

## Development

Here are the guidelines for development process. 

### Environment

Create `.envrc` file, that contains necessary environment variables using existing
`.envrc.template` - some of the variables may not be set - fill the gaps.
For the missing password please refer to the Secret manager in GCP project.

Then export environment variables from the created `.envrc ` file:
```sh
source .env.yaml
```

**Highly recommended** to use `direnv` for automation of this procedure.

### Notebooks

To run a Jupyter Notebook:
```sh
make notebook
```

### Adding new packages

To add a `python-package` to the repository use:
```sh
poetry add <python-package-name>
```

Alternatively to add a `python-package` dev-only dependency use:
```sh
poetry add --dev <python-package-name>
```

### Tests

All the components should have tests stored in the `codes.tests` directory. `Pytest` is
already configured.

You can run tests with:

```sh
make test
```

### Before you commit

Before every commit you should run:
```sh
make pre-commit
```
It will perform linting, spell and type checks and finally tests. Additionally, it will run "pip freeze" to lock 
requirements according to the `poetry.lock` file.

You can run the formatting separately by:
```sh
make format
```

Each step of the formatting/linting process can be also executed in isolation, for example:

```sh
make lint
make black
```

The **preferred merge method** is `fast-forward`.

For further possible methods check the `Makefile`.
