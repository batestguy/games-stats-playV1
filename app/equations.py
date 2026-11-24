"""Split authored equation markup into plain text and LaTeX fragments."""

import re


_INLINE_MATH = re.compile(r"\$([^$\r\n]+)\$")


def equation_parts(markup):
    return [(index % 2 == 1, part.strip())
            for index, part in enumerate(_INLINE_MATH.split(markup)) if part.strip()]


def choice_parts(markup):
    if not markup:
        return []
    return equation_parts(markup) if "$" in markup else [(True, markup)]
