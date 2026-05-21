.. _contributing:

================
For Contributors
================

`Open Agent Specification <https://github.com/oracle/agent-spec/>`_ (hereinafter referred to as **Agent Spec**) is a platform-agnostic configuration language designed to define AI Agents and their workflows.
It is developed and maintained by Oracle.
Oracle believes that Agent Spec will contribute to standardizing agents development and have open-sourced its specification to encourage community contributions.
Find the sources at `GitHub <https://github.com/oracle/agent-spec/>`_.

If you work on the agentic framework or library that implements Agent Spec components, and have a specific feature request or come across a potential issue, you can proceed by:

- Submitting a `GitHub issue <https://github.com/oracle/agent-spec/issues>`_ for bug reports or questions.
- Submitting a Request for Comments (RFC) for a new feature request or enhancement.

As a contributor, we expect you to abide by the :doc:`Contributor Code of Conduct <conduct>`, which outlines the standards for respectful and constructive collaboration.

Submitting a GitHub Issue
=========================

Use GitHub's issue tracking system to report issues (bugs) or ask questions related to Agent Spec.
You can submit a GitHub issue `here <https://github.com/oracle/agent-spec/>`_.

When submitting a bug, provide a clear description of the problem.
We encourage you to:

- Include steps to reproduce the bug, so Agent Spec developers can replicate the problem.
- Attach error messages, logs, or screenshots to give more context to the issue.
- Mention the environment (operating system, version, etc.) where the bug occurs.

You GitHub issue will be triaged and you will get some feedback in a timely manner.

Submitting a Request for Comments (RFC)
=======================================

To propose a new feature or enhancement, submit a Request for Comments (RFC).
This RFC is basically a design proposal where you can share a detailed description of what change you want to make, why it is needed, and how you propose to implement it.

The RFC will be carefully assessed by the Agent Spec core development team.
It also gives the maintainers an opportunity to suggest refinements before you start coding.

Follow these instructions to submit an RFC.

I. Create an RFC
----------------

- Fork the `Agent Spec repository <https://github.com/oracle/agent-spec/>`_.
- Fill out your proposal using the :doc:`provided template <rfcs-template>`.
- Rename the template file to **RFC-your-feature-name.rst** and push it to your fork.
- `Submit a pull request (PR) <https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork>`_ titled **RFC-your-feature-name**.

Before your RFC is ready for review, give it the **draft** label.

II. Get Feedback on the RFC
---------------------------

- Once your RFC is ready, remove the draft label.
- File a GitHub issue against the `Agent Spec repository <https://github.com/oracle/agent-spec/>`_ with request to review your proposal.
- In the description, include a short summary of your feature and a link to your RFC pull request.

The Agent Spec development team will review your RFC and get back with some feedback.
Revise your proposal as needed until everyone agrees on a path forward.

Implementing Your Proposal
==========================

If your RFC is accepted, you can begin working on the implementation.

I. Submit a Pull Request
------------------------

`Create and submit a PR <https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork>`_ from your fork with the code changes.
Be sure to link your PR to the accepted RFC so reviewers can easily catch up on the context and design decisions behind your proposal.

Once you submit a PR, CI service will run some sanity checks on your change.
Be sure to address any obvious issues caught by these checks (for example, formatting violation).

It is recommended to address one feature request per PR.

II. Sign the Oracle Contributor Agreement
-----------------------------------------

To allow your pull request to be accepted, you need to sign the `Oracle Contributor Agreement (OCA) <https://oca.opensource.oracle.com/>`_.
Sign it online, and once your name appears on the OCA signatory list, your pull request will be authorized.
If you signed the agreement, but the bot leaves a message that you have not signed the OCA, leave a comment on the pull request.
If it appears to be a delay, please send an email to *oracle-ca_us@oracle.com*.

III. Review and Merge
---------------------

Then it takes the form of a regular PR review.
An Oracle employee, a member of a working group, reviews and/or proposes more changes and, once it is in a mergeable state, will take responsibility for merging it into the main branch.

Contributing to Documentation
-----------------------------

We believe Agent Spec can contribute to standardizing agent development and have open-sourced its specification to encourage community contributions.
We hope this will foster an ecosystem of interchangeable and reusable designs and tools for agentic AI development.

The `Agent Spec documentation <https://oracle.github.io/agent-spec/index.html>`_ is open source, and everyone is welcome to help make it more complete.
If you consider contributing to the documentation, read the :doc:`Agent Spec writing guidelines <style_guide>` beforehand to ensure consistency and quality.

The End
-------

Oracle welcomes contributions to Agent Spec from users and developers alike!

—The Agent Spec Team
