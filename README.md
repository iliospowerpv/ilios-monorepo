Ilios APIs
--------

### Quickstart
1. Make sure the specified PostreSQL 16 instance is running, Python 3.12+ is installed.
2. Create and activate virtual environment
   - ``python3 -m venv venv``
   - For *nix systems: ``source venv/bin/activate``. For Windows: ``venv\Scripts\activate.bat``.
3. Install requirements.

   ``pip3 install -r requirements.txt``

   Please, note, that the app has several requirement files, split depending of they purpose:
   1. `requirements.txt` - the main set of dependencies to have application running;
   2. `requirements_dev.txt` - contains development related packages, such as code analyzers/linters;
   3. `requirements_test.txt` - includes testing related dependencies.
4. Set up environment variables based on the env.example file (copy it renaming to `.env`
and populate with values specific for your local machine).
5. Run the app.
   1. Manual

      ``uvicorn app.main:app --reload --port 8000 --log-config=log_conf.yaml``

      Check that app is running correctly going to the ``http://127.0.0.1:8000/health`` endpoint.

      The docs are available at ``http://127.0.0.1:8000/docs``
   3. Via Make utility
      - ``make run``

**NOTE:** psycopg2-binary support for M1 chipset:
 - ``brew install postgres``
 - ``pip install -r requirements.txt``

### Development
1. Make sure to use `utcnow` from models.helpers for any datetime field written into DB.

### Testing

#### Unit testing
Before executing tests set the env var with `export test_db_name=ilios_test_db`.

(NOTE: it should be different DB to prevent cleanup of DB used for your local development).

Use `pytest` or `make test` to launch unit-tests.

You can also execute `pytest --cov-report=html` to generate HTML pages with detailed coverage report per line (accessible at `htmlcov/index.html`).

#### Load testing
Before executing load tests ensure you populate required settings. Use `env-locust.example` to create own `.env-locust` instance.

To start testing server, use `locust -f locust_tests/locustfile.py --host=http://localhost:8000`.
When, go to the `http://127.0.0.1:8089/`, and you should be able to adjust the settings, such as number of users or testing host.
By default, it will be set to 1 user and host provided in the start script parameter (`http://localhost:8000`),
but are able to change it if you want, for example, perform tests on UAT environment.

Alternatively, you can use `make locust` command.




### Useful hints

#### Make
The utility contains list of commands to simplify development process.
1. `make help` - display full list of available actions
2. `make black` - run Black code formatter
3. `make lint` - run Flake8 analyzer with installed addons
4. `make test` - run Pytest and check code coverage gate
5. `make check` - run Black, Flake8 and Pytest together
6. `make run` - launch FastAPI and open docs in the browser
7. `make up-patch` - implements bump2version patch version update
8. `make up-minor` - implements bump2version minor version update
9. `make up-major` - implements bump2version major version update
10. `make notes` - run Python script to collect release notes
11. `make locust` - starts Locust server and open it homepage in browser

#### Bump2version
The utility allows to update the package version to follow [semantic versioning](https://semver.org/#semantic-versioning-specification-semver) practices:
1. `bump2version major --allow-dirty` - updates major version
2. `bump2version minor --allow-dirty` - updates minor version
3. `bump2version patch --allow-dirty` - updates patch version
4. `bump2version major --allow-dirty --new-version 1.2.3` - set specific version

#### pre-commit hooks
Git hook scripts are useful for identifying simple issues before submission to code review.
We run our hooks on every commit to automatically point out issues in code such as missing semicolons,
trailing whitespace, debug statements, failing lints or tests.

The tool should be already installed during your local project setup from `requirements_dev.txt`, although it is not
enabled yet. To enable it for your local git execute:

`pre-commit install`

Since now, all commits will start with pre-commit hooks configured at `.pre-commit-config.yaml`. If at least one of the
checks fails the commit won't happen. Instead, you'll see the report on what is wrong. And even for some hooks the
pre-commit tool can apply auto-fixes, so you may want to add the updated files to the git stage.

To run checks without executing a commit commands:

`pre-commit run --all-files`

To get your commit through without running that pre-commit hook, use the `--no-verify` option for `git commit` command,
e.g.:

`git commit -m "Hot-fix for cold storage" --no-verify`

Not all hooks are perfect, so sometimes you may need to skip execution of one or more specific hooks. pre-commit
solves this by querying a `SKIP` environment variable. The `SKIP` environment variable is a comma separated list of hook
ids. This allows you to skip a single hook instead of --no-verifying the entire commit.

`export SKIP=unit-tests,version-bump-up; gcmsg "Really important hot-fix for cold storage"`

If after some time you don't need to skip some hooks just unset the var:

`unset SKIP`
