# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
Test that pyagentspec does not alter the root log level and
respects the logger configuration provided by the application.
"""

import logging


def test_pyagentspec_logging_does_not_alter_application_logger():
    # When application provides a loggingconfig
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    assert root_logger.getEffectiveLevel() == logging.INFO

    # Then pyagentspec should not alter root loglevel
    assert root_logger.getEffectiveLevel() == logging.INFO

    # instead it should use the application logger
    assert logging.getLogger("pyagentspec").getEffectiveLevel() == logging.INFO

    # similar to how named loggers in the primary application behave
    app_logger = logging.getLogger("my.application")
    assert app_logger.getEffectiveLevel() == logging.INFO


if __name__ == "__main__":
    test_pyagentspec_logging_does_not_alter_application_logger()
