Line-to-Line Correspondence
===========================

CAF.space also provides a separate CLI entry point for line correspondence:

.. code-block:: bash

    caf.space.line_to_line path/to/line_to_line.yml

Configuration
-------------

Use a YAML config file with one reference network and one or more target networks.
An example config is available at ``examples/line_to_line.yml``.

Output QA warnings
------------------

During runtime, CAF.space emits warnings when correspondence quality checks detect:

* overlap length greater than the target link length;
* zero overlap length;
* invalid overlap values (negative or NaN);
* no correspondence rows for a target.

These warnings indicate that outputs should be reviewed manually before downstream use.

Current process limitations
---------------------------

The current line-to-line process has important limitations:

* correspondence is heuristic (buffer + angle + geometric distance), so complex
  junctions can still produce poor matches;
* MultiLineString geometries are merged where possible, but problematic geometries
  can still be dropped or mismatched;
* quality checks warn about suspicious outputs but do not automatically reject
  or correct them;
* there is no built-in acceptance threshold for final output quality, so manual
  validation remains required.
