:orphan:

=========================
Documentation Style Guide
=========================

This style guide is short but specific to the Agent Spec documentation, and aligns with the writing guidelines of the Oracle Documentation Style Guide.
These recommendations apply universally across all documentation types—be it reference materials, how-to guides, or release notes.
We do not enforce these recommendations, but following them will improve content readability and ensure consistency across all pages.

I. Naming conventions
---------------------

- Use **Agent Spec** for the name of the specification, all letters capital. It is a proper name; no article is required upfront. Example: *Agent Spec is a portable, platform-agnostic configuration language.*
- Use **PyAgentSpec** for a Python SDK name implemented on top of Agent Spec. It is a proper name; no article is required upfront.
- Use **Agent** and **Flow** with initial letters capitalized when referring to the concepts or class names; otherwise, use lowercase.
- There is no class/API such as **Assistant**. You can create intelligent assistants. Example: *With PyAgentSpec users can build Agent Spec-compliant agents.*

II. Verb tense
--------------

In technical documentation, the verb tense depends on the context, but the general guidelines are:

-  Present tense – Most common, recommended, used for describing facts, or how a system behaves. Example: *The user inputs their question to the assistant*.
-  Future tense – Used typically when describing planned features or expected behavior. Example: *The next release will include support for the Swarm class to build a swarm of agents.*
-  Past tense – Rarely used, except when documenting historical changes or past events. Example: *Version 1.1 introduced support for the Swarm class.*

For Agent Spec documentation, the present tense is preferred.

III. Style and tone
-------------------

Be conversational and yet keep some level of formality.

-  Avoid marketing pitch language in the technical documentation.
-  **Use the second-person singular, *you*.** Try to use *we* only when referring to developers. Example: *We are still working on implementing*; *We recommend*.
-  Avoid using passive voice extensively, and rewrite the sentence to active voice. Instead of writing *It is recommended*, use *We recommend*.
-  Avoid phrasing in terms of *Let’s do something*.
-  Avoid using phrases such as *It’s simple*, *It’s easy*.
-  Avoid using contractions such as *it’s*, *you’ll*, *you’re*.
-  Avoid the use of gender-specific, third-person pronouns such as *he*, *she*, *his*, and *hers*. If possible, rewrite to use a neutral plural subject, such as *developers* or *users*.
-  Try to avoid using *get*. Instead of writing *To check which classes got supported*, use *To check which classes are supported*.

Be clear:

-  The introduction to a how-to guide can be as simple as *In this guide you will learn how to…*
-  Consider including a short introduction and a summary for the guide.
-  Consider a closing sentence summing the section up.
-  Double check the logical flow of the chapter outline.
-  Avoid redundancy or content duplication.
-  Always proofread and when proofreading, read it out loud. It will help you find passages that may be too long or bulky.
-  Try not to let sentences get too long and serpentine. When in doubt, make it two sentences.
-  If one sentence goes to three lines, consider breaking it up.

IV. Formatting rules
--------------------

The following inconsistencies are important, common, and worth paying special attention to.

Page titles and subtitles
~~~~~~~~~~~~~~~~~~~~~~~~~

-  **Main page title should have the first letter of each word capitalized except for articles or prepositions**. If a title contains a hyphenated term, each word should be capitalized, unless it is a preposition or article. Example: *How-to Guides*.
-  **All subheadings should be sentence case**.
-  If you write a how-to guide, start with an **action verb**. Example: *Execute Agent Spec Assistants with Different Frameworks*.
-  If you write a reference documentation, it should start with a **noun or gerund**. Example: *Testing Inference with LLMs*.

Spacing
~~~~~~~

-  Break the line if the sentence is getting long.
-  Strive not to have code (lowercase) start sentences.

Referring to a file name or path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To refer to a file name or repository path inside the text, italicize it. Example: "Save this code to a file named *File.py* in the current working directory."

Button names in the text
~~~~~~~~~~~~~~~~~~~~~~~~

-  When documenting the UI or API, match the terminology. Example: *To stop the process, click Abort*.
-  Capitalize the button name (as it is onscreen).

Referring to file formats
~~~~~~~~~~~~~~~~~~~~~~~~~

-  When referring to a typical file format in the text, capitalize each letter. Example: JAR and JSON, not jar and json.
-  Do not italicize types of files.

Oxford comma
~~~~~~~~~~~~

The **Oxford comma** is the comma before words such as “and” or “or” in a list of three or more items.
Example: *The agent needs to be given a name, an LLM configuration, and a system prompt.*

**We suggest using the Oxford comma** to keep sentences as clear and intelligible.

British English vs American English spelling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As a convention, Oracle Corporation uses American English spelling rather than British English spelling.
Use **American English spelling**.

-  Example: Instead of "…our", use "…or". Write *behavior*, not *behaviour*.
-  Example: **Instead of "…ise", use "…ize"**. Write *organize* and *organization*, not *organise* and *organisation*.

How to become a contributor
---------------------------

The Agent Spec documentation is open source.
If you consider contributing to it, please read our :doc:`contributing guidelines <contributing>`.

The end
~~~~~~~

We thank you for taking the time to read this style guide.

The Agent Spec team
