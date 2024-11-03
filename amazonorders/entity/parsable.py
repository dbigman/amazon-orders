__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import logging
from typing import Any, Callable, Optional, Type, Union, Dict

from bs4 import Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrderEntityError, AmazonOrdersError

logger = logging.getLogger(__name__)


class Parsable:
    """
    A base class that contains a parsed representation of the entity, and can be extended to
    be made up of the entities fields utilizing the helper methods.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        #: Parsed HTML data that can be used to populate the fields of the entity.
        self.parsed: Tag = parsed
        #: The AmazonOrdersConfig to use.
        self.config: AmazonOrdersConfig = config

    def __getstate__(self) -> Dict:
        state = self.__dict__.copy()
        state.pop("parsed")
        return state

    def safe_parse(self,
                   parse_function: Callable[..., Any],
                   **kwargs: Any) -> Any:
        """
        Execute the given parse function on a field, handling any common parse exceptions and passing
        them as warnings to the logger, suppressing them as exceptions.

        :param parse_function: The parse function to attempt safe execution.
        :param kwargs: The ``kwargs`` will be passed to ``parse_function``.
        :return: The return value from ``parse_function``.
        """
        if not parse_function.__name__.startswith("_parse_") and parse_function.__name__ != "simple_parse":
            raise AmazonOrdersError("The name of the `parse_function` passed "
                                    "to this method must start with `_parse_`.")

        try:
            return parse_function(**kwargs)
        except (AttributeError, IndexError, ValueError):
            logger.warning(
                "When building {name}, `{function}` "
                "could not be parsed.".format(name=self.__class__.__name__,
                                              function=parse_function.__name__.split(
                                                  "_parse_")[1]),
                exc_info=True)

    def simple_parse(self,
                     selector: Union[str, list],
                     link: bool = False,
                     text_contains: Optional[str] = None,
                     required: bool = False,
                     prefix_split: Optional[str] = None,
                     wrap_tag: Optional[Type] = None) -> Any:
        """
        Will attempt to extract the text value of the given CSS selector(s) for a field, and
        is suitable for most basic functionality on a well-formed page.

        The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each
        selector in the list will be tried.

        In most cases the selected tag's text will be returned, but if ``wrap_tag`` is given, the
        tag itself (wrapped in the class) will be returned.

        :param selector: The CSS selector(s) for the field.
        :param link: If a link, the value of ``src`` or ``href`` will be returned.
        :param text_contains: Only select the field if this value is found in its text content.
        :param required: If required, an exception will be thrown instead of returning ``None``.
        :param prefix_split: Only select the field with the given prefix, returning the right side of the split if so.
        :param wrap_tag: Wrap the selected tag in this class before returning.
        :return: The cleaned up return value from the parsed ``selector``.
        """
        if isinstance(selector, str):
            selector = [selector]

        value: Union[int, float, bool, str, None] = None

        for s in selector:
            for tag in self.parsed.select(s):
                if tag:
                    if link:
                        key = "href"
                        # Check if the link is being pulled from an <img> tag
                        if "src" in tag.attrs:
                            key = "src"
                        value = self.with_base_url(tag.attrs[key])
                    else:
                        if text_contains and text_contains not in tag.text:
                            continue

                        if prefix_split:
                            if prefix_split not in tag.text:
                                continue
                            else:
                                value = tag.text.strip().split(prefix_split)[1]
                        else:
                            value = tag.text

                        if wrap_tag:
                            value = wrap_tag(tag, self.config)
                        else:
                            value = util.to_type(value.strip())
                    break
            if value:
                break

        if not value and required:
            raise AmazonOrderEntityError(
                "When building {name}, field for selector `{selector}` was None, but this is not allowed.".format(
                    name=self.__class__.__name__, selector=selector))

        return value

    def safe_simple_parse(self,
                          selector: Union[str, list],
                          **kwargs: Any) -> Any:
        """
        A helper function that uses :func:`simple_parse` as the ``parse_function()`` passed to :func:`safe_parse`.

        :param selector: The selector to pass to :func:`simple_parse`.
        :param kwargs: The ``kwargs`` will be passed to ``parse_function``.
        :return: The return value from :func:`simple_parse`.
        """
        return self.safe_parse(self.simple_parse, selector=selector, **kwargs)

    def with_base_url(self,
                      url: str) -> str:
        """
        If the given URL is relative, the ``BASE_URL`` will be prepended.

        :param url: The URL to check.
        :return: The fully qualified URL.
        """
        if not url.startswith("http"):
            url = f"{self.config.constants.BASE_URL}{url}"
        return url

    def to_currency(self,
                    value: Union[str, int, float]) -> Union[int, float, None]:
        """
        Clean up a currency, stripping non-numeric values and returning it as a primitive.

        :param value: The currency to parse.
        :return: The currency as a primitive.
        """
        if isinstance(value, (int, float)):
            return value

        if not value:
            return None

        currency = util.to_type(
            value.strip().replace("$", "").replace(",", "")
        )

        if isinstance(currency, str):
            return None

        return currency
