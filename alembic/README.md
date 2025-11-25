### Generic single-database configuration.

---
## Deployment for alembic
The alembic deployment steps are present in the `cloudbuild*.yaml`

---
## Basics about alembic
To initialize the alembic async use
```shell
alembic init -t async alembic
```

To create alembic revision use
```shell
alembic revision --autogenerate -m "Initial setup"
```

To get head
```shell
alembic heads
```

To get current
```shell
alembic current
```

To get history
```shell
alembic history
```

To test the migration aka perform a dry-run. \
Note: alembic will apply migration to the DB but the changes will roll back when `-x dry-run` flag is used
```shell
alembic -x dry-run upgrade head
```

To apply changes
```shell
alembic upgrade head
```

<span style="color:red">***BE CAREFUL! Only use in DEV or QA env*** </span>\
To reset the entire DB
```shell
alembic downgrade base && alembic upgrade head
```

---

## Using alembic
### Prerequisite:
Create a `.env` file under project folder.
- add the variables required by `env.example`

### Perform:
For adding new model: \
Add new model to `app.models` and register the new models in `app.db.base`

For updating existing model: \
Make changes to model an existing model under `app.models`

After completing one or both the above steps use terminal/bash/commandline
```shell
# set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/PATH_TO_SERVICE_PIP_PACKAGE

# Generate revision
alembic revision --autogenerate -m "TYPE_MESSAGE_HERE"

# if the above command runs successfully a new revision file 
# will be created under PROJECT_ROOT/alembic/versions/
# alternatively use history command to check the change
alembic history
```

---
### <span style="color:red">Validation</span>
After the revision is created, \
Please manually validate the newly generated version file located under `PROJECT_ROOT/alembic/versions`
