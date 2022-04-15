import pathlib
from unittest import TestCase

from ditto.utils import collections, files, strings


class TestDittoCollectionsUtils(TestCase):
    def test_summarise_list(self) -> None:
        list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        func = lambda x: str(x * 2)

        summary = collections.summarise_list(*list)
        self.assertEqual(summary, "1, 2, 3, 4, 5, 6, 7, 8, 9, 10")

        summary = collections.summarise_list(*list, skip_first=True)
        self.assertEqual(summary, "2, 3, 4, 5, 6, 7, 8, 9, 10")

        summary = collections.summarise_list(*list, func=func)
        self.assertEqual(summary, "2, 4, 6, 8, 10, 12, 14, 16, 18, 20")

        summary = collections.summarise_list(*list, func=func, max_items=3)
        self.assertEqual(summary, "2, 4, 6 (+7 More)")

        summary = collections.summarise_list(*list, max_items=3, skip_first=True)
        self.assertEqual(summary, "2, 3, 4 (+6 More)")


class TestDittoFileUtils(TestCase):
    def test_get_base_dir(self) -> None:
        base_dir = files.get_base_dir()
        self.assertIsInstance(base_dir, pathlib.Path)
        self.assertEqual(base_dir, (pathlib.Path(__file__).parent.parent / "ditto").relative_to(pathlib.Path.cwd()))


class TestDittoStringUtils(TestCase):
    def test_codeblock(self) -> None:
        codeblock = strings.codeblock(None)
        self.assertEqual(codeblock, "```\nNone\n```")

        codeblock = strings.codeblock("2", language="3")
        self.assertEqual(codeblock, "```3\n2\n```")

    def test_yes_no(self) -> None:
        yes_no = strings.yes_no(False)
        self.assertEqual(yes_no, "No")

        yes_no = strings.yes_no(True)
        self.assertEqual(yes_no, "Yes")

        yes_no = strings.yes_no(None)
        self.assertEqual(yes_no, "No")

        yes_no = strings.yes_no(1)
        self.assertEqual(yes_no, "Yes")

    def test_as_columns(self) -> None:
        items = [str(x) for x in (1, 2, 3, 4, 5, 6)]

        _items_in_col = strings._items_in_col(6, 2)
        self.assertEqual(_items_in_col, (3, 3))

        _transpose = strings._transpose(items, 2)
        self.assertEqual(_transpose, ["1", "4", "2", "5", "3", "6"])

        columns = strings.as_columns(items)
        self.assertEqual(columns, "1 2\n3 4\n5 6\n")

        columns = strings.as_columns(items, transpose=True)
        self.assertEqual(columns, "1 4\n2 5\n3 6\n")

        items = [str(x) for x in (1, 2, 3, 4, 5, 6, 7)]

        _items_in_col = strings._items_in_col(7, 2)
        self.assertEqual(_items_in_col, (4, 3))

        _transpose = strings._transpose(items, 2)
        self.assertEqual(_transpose, ["1", "5", "2", "6", "3", "7", "4"])

        columns = strings.as_columns(items)
        self.assertEqual(columns, "1 2\n3 4\n5 6\n7\n")

        columns = strings.as_columns(items, transpose=True)
        self.assertEqual(columns, "1 5\n2 6\n3 7\n4\n")

    def test_ordinal(self) -> None:
        ordinal = strings.ordinal(1)
        self.assertEqual(ordinal, "1st")

        ordinal = strings.ordinal(2)
        self.assertEqual(ordinal, "2nd")

        ordinal = strings.ordinal(3)
        self.assertEqual(ordinal, "3rd")

        ordinal = strings.ordinal(4)
        self.assertEqual(ordinal, "4th")

        ordinal = strings.ordinal(61)
        self.assertEqual(ordinal, "61st")

    def test_regional_indicator(self) -> None:
        indicator = strings.regional_indicator("A")
        self.assertEqual(indicator, "\N{REGIONAL INDICATOR SYMBOL LETTER A}")

        indicator = strings.regional_indicator("z")
        self.assertEqual(indicator, "\N{REGIONAL INDICATOR SYMBOL LETTER Z}")

    def test_keycap_digit(self) -> None:
        digit = strings.keycap_digit("1")
        self.assertEqual(digit, "1\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}")

        digit = strings.keycap_digit(9)
        self.assertEqual(digit, "9\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}")

        digit = strings.keycap_digit("10")
        self.assertEqual(digit, "\U000FE83B")
