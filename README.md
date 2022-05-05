# SiWECAL-TB-monitoring

[![Tests on dummy data](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/actions/workflows/tests-on-dummy-data.yml/badge.svg)](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/actions/workflows/tests-on-dummy-data.yml)
[![pre-commit](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/actions/workflows/pre-commit.yml)
![GitHub repo size](https://img.shields.io/github/repo-size/SiWECAL-TestBeam/SiWECAL-TB-monitoring)

Event-based almost-online monitoring for the SiW ECAL.
To get started, check out the [tutorial](./Tutorial-TB2022-03.md).

## Submodules

The monitoring procedure interacts closely with code from the
[SiWECAL-TB-analysis repository](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-analysis).
In many places (conversion, event building) will directly call the analysis code.
Therefore each commit in the monitoring repository can only be expected to work
with a specific commit from the analysis repository.
This relationship is represented by tracking the analysis repository as a
_git submodule_.


The TLDR for using a repository with submodules:

- Download the repository into `monitoring`

  ```bash
  git clone git@github.com:SiWECAL-TestBeam/SiWECAL-TB-monitoring.git --recurse-submodules  --shallow-submodules monitoring
  ```

- Get the submodules after having cloned without `--recurse-submodules`

  ```bash
  git submodule update --init --recursive
  ```

- Get upstream changes

  ```bash
  git pull --recurse-submodules
  ```

  - This will give you the newest version of monitoring.
    If (and only if) the monitoring is now based on a newer version of its
    submodules (SiWECAL-TB-analysis), the submodules will be updated to that commit.

- _For developers:_ Get the newest version of the submodules

  ```bash
  git submodule update --remote --recursive
  ```

  - Do this if you want to adapt the monitoring for working with a newer version
    of the analysis repository.
  - _Temporary note:_ Warning: As I am currently the only active developer,
    I found it simpler to track
    [_my fork_](https://github.com/kunathj/SiWECAL-TB-analysis) as a submodule
    (see [.gitmodules](./.gitmodules)).
    Thus `submodule update` will go to this fork's last commit,
    which might be different from upstream.

For more information on git submodules we recommended the
[submodules chapter](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
of the Git Pro book.

## Useful web links

- [ROOT docs for Draw()](https://root.cern/doc/master/classTTree.html#a73450649dc6e54b5b94516c468523e45)
- [Python logging and multiprocessing](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes)
- [ROOT example workflow with Chain and Draw](https://root.cern.ch/root/htmldoc/guides/users-guide/ExampleAnalysis.html)
- [emojis (only use 1-codepoint ones though)](https://emojipedia.org/emoji/)
