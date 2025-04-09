"""Functions for finding Cookiecutter templates and other components."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from cookiecutter.exceptions import NonTemplatedInputDirException

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Issue 1: Logging level is set globally in a module


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: The Jinja2 environment instance.
    :return: Relative path to project template.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    if not os.path.isdir(repo_dir):  # Issue 2: Defensive check missing in original, but...
        return None  # Issue 3: Violates function return type (should raise or return Path)

    for str_path in os.listdir(repo_dir):
        if (
            'cookiecutter' in str_path
            and env.variable_start_string in str_path
            and env.variable_end_string in str_path
        ):
            project_template = Path(repo_dir, str_path)
            break
    else:
        raise NonTemplatedInputDirException  # Could be more informative (optional stretch)

    logger.debug('The project template appears to be %s', project_template)
    return project_template

# Issue 4: No __main__ or test scaffolding; consider adding unit tests or CLI stub