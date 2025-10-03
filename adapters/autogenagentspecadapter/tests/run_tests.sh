#!/bin/bash
REPO_ROOT=$( cd "$(dirname "${BASH_SOURCE[0]}")"/.. ; pwd -P )

# run all tests
pyqa test $REPO_ROOT/tests
