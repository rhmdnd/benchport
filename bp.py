#!/usr/bin/env python

import argparse
import json
import re
import subprocess
import unittest


parser = argparse.ArgumentParser('Parse information from benchmarks')

parser.add_argument(
    'benchmark', type=str,
    help='File path to benchmark in PDF format'
)
parser.add_argument(
    '-c', '--control', type=str,
    help='Control ID to parse and print to stdout in YAML (e.g, 1.1.2).'
)

args = parser.parse_args()

class Control(dict):
    def __init__(self, raw):
        self._raw = raw
        self.section = self._parse_section()
        self.title = self._parse_title()
        self.description = self._parse_description()
        self.rationale = self._parse_rationale()
        self.impact = self._parse_impact()
        self.profile_applicability = self._parse_level()
        # Add support for audit and remediation parsing

    def __dict__(self):
        return {
            'section': self.section,
            'title': self.title,
            'description': self.description,
            'rationale': self.rationale,
            'impact': self.impact,
            'profile_applicability': self.profile_applicability}

    def _parse_description(self):
        pattern = re.compile(r'(?<=Description:\s)[\w]+[\w \s \.,-]*(?=[\s\n]Rationale:)')
        m = pattern.search(self._raw)
        if m:
            return m[0].replace('\n', ' ')

    def _parse_rationale(self):
        pattern = re.compile(r"(?<=Rationale:\s)[\w\s\n.,'-]*(?=\sImpact:)")
        m = pattern.search(self._raw)
        if m:
            return m[0].replace('\n', ' ')

    def _parse_impact(self):
        pattern = re.compile(r"(?<=Impact:\s)[\w]+[\w \s \.,:'-]*(?=[\s\n]Audit:)")
        m = pattern.search(self._raw)
        if m:
            result = m[0].replace('\n', ' ')
            if result == 'None':
                return None
            return result

    def _parse_section(self):
        pattern = re.compile(r'\d.\d.\d+')
        m = pattern.search(self._raw)
        if m:
            return m[0].lstrip().rstrip()

    def _parse_title(self):
        pattern = re.compile(r'(?!\d.\d.\d) [\w \d \s()]*(?=Profile Applicability)')
        m = pattern.search(self._raw)
        if m:
            return m[0].replace('\n', ' ').lstrip().rstrip()

    def _parse_level(self):
        pattern = re.compile(r'Level \d')
        m = pattern.search(self._raw)
        if m:
            return m[0].lstrip().rstrip()


def convert_pdf(path, format='text'):
    if format == 'text':
        binary = 'pdftotext'
        output_file = '/tmp/pdf-out.text'
    elif format == 'html':
        binary = 'pdftohtml'
        output_file = '/tmp/pdf-out.html'
    else:
        raise Exception('Unsupported format')

    command = [binary, path, output_file]
    subprocess.run(command, capture_output=True, check=True)

    with open(output_file, 'r') as f:
        return f.read()


# FIXME: This is kind of a mess. Since the regular expressions below only match
# the titles, we need to use their boundaries to parse the actual details of
# the control. Here we're looking backwards in the list to find the character
# we should start parsing. This is a quick hack and should be handled in more
# intuitive ways so it's easier to load controls from a raw benchmark. For now,
# keep the mess contained to this method.
def to_dict(raw_text):
    # Try and find the first section of the document (e.g., 1. Section Name) by
    # building a regular expression and using the end index of the match, if
    # there is one. This helps us cut to the meat of the benchmark.
    start = 0
    pattern = re.compile(r'\n\d [\w ]*\n')
    match = pattern.search(raw_text)
    if match:
        start = match.end()

    # This pattern attempts to match the control title, which usually starts
    # with integers and some text that uniquely identifies the control.
    pattern = re.compile(r'(?!.*\.{2})\d*\.\d*\.\d+ [\w :()-./]*\n')
    match = pattern.search(raw_text)

    # Save the benchmark in a dictionary, where the key is the control section
    # (e.g., 1.1.1, 5.2.10) and the value is the corresponding Match object,
    # which contains start and end indexs we can use in later searches. The
    # Match object only corresponds to the title, not the entire control
    # substring.
    control_indexes = {}
    while True:
        match = pattern.search(raw_text, start)
        if match:
            section = match[0].split()[0]
            control_indexes[section] = match
            start = match.end()
        else:
            break

    controls = {}
    last_control = None
    last_section = None
    for section, match in control_indexes.items():
        if last_control is None:
            last_control = match
            last_section = section
            continue
        raw_control = raw_text[last_control.start():match.start()]
        controls[last_section] = Control(raw_control)
        last_control = match
        last_section = section

    raw_control = raw_text[last_control.start():len(raw_text)]
    controls[last_section] = Control(raw_control)
    return controls


class TestConversion(unittest.TestCase):

    def test_to_dict(self):
        with open('./test.txt', 'r') as f:
            self.raw_text = f.read()

        # Make sure we get back a dictionary of Match objects for each control
        # section where the keys are the control sections (e.g., 1.1.1).
        actual = to_dict(self.raw_text)
        self.assertIsInstance(actual, dict)
        self.assertTrue(len(actual.keys()) == 7)
        sections = [
            '1.1.2', '1.1.2', '1.1.10', '1.1.11', '1.1.12', '1.1.13', '1.1.14']
        for expected in sections:
            self.assertIn(expected, actual.keys())
            self.assertIsInstance(actual[expected], Control)


class TestControl(unittest.TestCase):

    def setUp(self):
        with open('./test.txt', 'r') as f:
            raw_text = f.read()
            self.controls = to_dict(raw_text)

    def test_description(self):
        control = self.controls['1.1.1']
        expected = (
            'Lorem ipsum dolor sit amet, qui minim labore adipisicing minim '
            'sint cillum sint consectetur cupidatat.')
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.2']
        expected = 'Nostrud officia pariatur ut officia.'
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.10']
        expected = (
            'Sit irure elit esse ea nulla sunt ex occaecat reprehenderit '
            'commodo officia dolor Lorem duis laboris cupidatat officia.')
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.11']
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.12']
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.13']
        self.assertEqual(control.description, expected)

        control = self.controls['1.1.14']
        self.assertEqual(control.description, expected)

    def test_profile_applicability(self):
        control = self.controls['1.1.1']
        self.assertTrue(control.profile_applicability == 'Level 1')

        control = self.controls['1.1.2']
        self.assertTrue(control.profile_applicability == 'Level 2')

        control = self.controls['1.1.10']
        self.assertTrue(control.profile_applicability == 'Level 1')

        control = self.controls['1.1.11']
        self.assertTrue(control.profile_applicability == 'Level 2')

        control = self.controls['1.1.12']
        self.assertTrue(control.profile_applicability == 'Level 1')

        control = self.controls['1.1.13']
        self.assertTrue(control.profile_applicability == 'Level 1')

        control = self.controls['1.1.14']
        self.assertTrue(control.profile_applicability == 'Level 1')

    def test_section(self):
        control = self.controls['1.1.1']
        self.assertTrue(control.section == '1.1.1')

        control = self.controls['1.1.2']
        self.assertTrue(control.section == '1.1.2')

        control = self.controls['1.1.10']
        self.assertTrue(control.section == '1.1.10')

        control = self.controls['1.1.11']
        self.assertTrue(control.section == '1.1.11')

        control = self.controls['1.1.12']
        self.assertTrue(control.section == '1.1.12')

        control = self.controls['1.1.13']
        self.assertTrue(control.section == '1.1.13')

        control = self.controls['1.1.14']
        self.assertTrue(control.section == '1.1.14')

    def test_rationale(self):
        control = self.controls['1.1.1']
        expected = (
            'Lorem ipsum dolor sit amet, officia excepteur ex fugiat '
            'reprehenderit enim labore culpa sint ad nisi Lorem pariatur '
            'mollit ex esse exercitation amet.')
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.2']
        expected = (
            'Lorem ipsum dolor sit amet, qui minim labore adipisicing minim '
            'sint cillum sint consectetur cupidatat.'
        )
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.10']
        expected = (
            'Aliqua reprehenderit commodo ex non excepteur duis sunt velit '
            'enim.')
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.11']
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.12']
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.13']
        self.assertEqual(control.rationale, expected)

        control = self.controls['1.1.14']
        self.assertEqual(control.rationale, expected)

    def test_impact(self):
        control = self.controls['1.1.1']
        self.assertIsNone(control.impact)

        control = self.controls['1.1.2']
        expected = (
            'Voluptate laboris sint cupidatat ullamco ut ea consectetur et est '
            'culpa et culpa duis.')
        self.assertEqual(control.impact, expected)

        control = self.controls['1.1.10']
        self.assertEqual(control.impact, expected)

        control = self.controls['1.1.11']
        self.assertEqual(control.impact, expected)

        control = self.controls['1.1.12']
        self.assertEqual(control.impact, expected)

        control = self.controls['1.1.13']
        self.assertEqual(control.impact, expected)

        control = self.controls['1.1.14']
        self.assertEqual(control.impact, expected)


if __name__ == "__main__":
    raw = convert_pdf(args.benchmark)
    controls = to_dict(raw)
    # This is a rudimentary example showing the details of a specific control,
    # if supplied. This CLI needs to be worked out depending on how or if this
    # is actually used for something.
    if args.control:
        if args.control in controls.keys():
            print(json.dumps(controls[args.control].__dict__()))
    else:
        output = []
        for section, control in controls.items():
            output.append(control.__dict__())
        print(json.dumps(output))
