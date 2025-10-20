#!/bin/bash
#
# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# This cannot be tested in a pytest, which has its own rootLogger to communicate activity.
TESTS_DIR=$1

echo "#################################### LOGGER NULL TEST ######################################";

python $TESTS_DIR/check_rootLogger_handles_are_null.py
if [ $? -ne 0 ]; then
    echo "A StreamHandler was attached to the rootLogger on importing the pyagentspec package. FAILING Logging tests."; exit 1;
else
    echo "TEST PASSED."
fi

echo "#################################### UNDEFINED LOGGER TEST ######################################";

python $TESTS_DIR/check_undefined_logger.py
if [ $? -ne 0 ]; then
    echo "When application provides a loggingconfig, pyagentspec should not alter root loglevel instead it should use the application logger similar to how named loggers in the primary application behave"; exit 1;
else
    echo "TEST PASSED."
fi
