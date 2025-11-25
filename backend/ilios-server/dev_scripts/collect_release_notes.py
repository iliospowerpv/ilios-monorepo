# flake8: noqa: T201
"""Prepare release notes for the BE releases to represent features to be delivered"""

import re
from subprocess import check_output


def _fetch_develop():
    print("1. Fetching latest develop branch metadata...")
    check_output(["git", "fetch", "origin", "develop"])


def _find_diff():
    print("2. Retrieving latest commit from the main branch and it's timestamp to find main VS develop branches diff...")
    main_commit_hash = check_output("git log -n 1 origin/main --pretty=format:%H", shell=True).decode("utf-8").strip()
    main_commit_ts = (
        check_output(f"git show --no-patch --format=%ci {main_commit_hash}", shell=True).decode("utf-8").strip()
    )
    commits_since_release = (
        check_output(f'git log origin/develop --pretty=format:%H --since="{main_commit_ts}"', shell=True)
        .decode("utf-8")
        .strip()
        .split("\n")
    )
    # remove the latest main commit since it appears in the diff list
    if main_commit_hash in commits_since_release:
        commits_since_release.remove(main_commit_hash)

    return commits_since_release


def _extract_pr_number(commit_message):
    # regex pattern to find the PR number in parentheses preceded by a #
    pattern = r"#(\d+)"
    match = re.search(pattern, commit_message)

    if match:
        return f"#{match.group(1)}"

    return None


def _retrieve_pr_details(commits_since_release):
    print("3. Find PRs to be released to the main...")
    associated_pr_ids = list()
    for commit_hash in commits_since_release:
        commit_details = (
            check_output(f'git log --pretty=format:"%H %s" develop | grep {commit_hash}', shell=True)
            .decode("utf-8")
            .strip()
        )
        associated_pr_number = _extract_pr_number(commit_details)
        if associated_pr_number:
            associated_pr_ids.append(associated_pr_number)
            continue
        print(f"Please, pay attention! Cannot retrieve PR ID for the commit: <{commit_details}>")
    return associated_pr_ids


def _print_notes(associated_pr_ids):
    print("4. Here we go! Please, find release notes below.\n")
    associated_pr_ids.reverse()
    for index_, associated_pr_id in enumerate(associated_pr_ids, start=1):
        print(f"{index_}. {associated_pr_id}")


def generate_release_notes():
    # fetch latest develop to ensure you include all comments to the diff
    _fetch_develop()

    # find commits difference since latest release
    commits_since_release = _find_diff()

    if not commits_since_release:
        print("Oops! It seems there are no commits in difference, finishing the execution")
        return

    # process fetching related PRs
    associated_pr_ids = _retrieve_pr_details(commits_since_release)

    # print out release notes in the asc order
    _print_notes(associated_pr_ids)


if __name__ == "__main__":
    generate_release_notes()
