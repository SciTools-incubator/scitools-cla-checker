# SciTools CLA checker

## Setup

In order to use this tool, it is necessary to have a [Personal Access Token](https://github.com/blog/1509-personal-api-tokens)
with a scope including ``repo: public_repo``, ``repo: repo:status``. The token must be available as the environment variable ``TOKEN``.


The package requires python 3, the dependencies can be seen in the [requirements file](requirements.txt), or installed with:

```
pip install -r requrements.txt
```


## CLI Usage

The CLA checker has the ability to print all CLA signatories:

```
>>> python -m scitools_cla_checker
signatory1
signatory2
...
```

Checking a contributors exists in the signatories may be done with:

```
>>> python -m scitools_cla_checker ${github_login_to_check}
<login> is in the list of contributors
```

Updating a pull request's CLA status and label from the command line may be done with:

```
>>> python -m scitools_cla_checker.update_pr ${REPO_OWNER}/${REPO_NAME} ${PR_NUMBER}
```

Note: This will set a GitHub status of either failure or success, and if failure, add the label "Blocked: CLA needed"


Checking an entire repository for CLA coverage (no equivalent webservice)

```
>>> python -m scitools_cla_checker.check_repo SciTools/iris
```

## Webapp Usage

This tool has been developed primarily to run as a web application that is triggered each time a pull request is modified.
In order to achieve this, we listen to GitHub organisation webhooks, and run the checker each time the webhook is called
with a pull-request event. The webapp itself is running on Heroku at https://scitools-cla-check.herokuapp.com/, and it has
been setup with a TOKEN environment variable (created by @pelson) to allow it to update the PRs as necessary. https://github.com/SciTools-incubator/scitools-cla-checker is the canonical source for the webapp, and each update to master is immediately deployed to the heroku webapp.


