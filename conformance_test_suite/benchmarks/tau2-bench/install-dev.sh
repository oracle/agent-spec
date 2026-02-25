#!/bin/bash
#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

git clone https://github.com/sierra-research/tau2-bench.git

cd tau2-bench
pip install -e . -c ../constraints/constraints.txt
cp ../patch_files/agent_spec_agent.py src/tau2/agent
