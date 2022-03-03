#!/usr/bin/env python

import argparse
import json
import re
import subprocess


class Control(dict):
    def __init__(self, raw):
        self._raw = raw
        self.section = self._parse_section()
        self.title = self._parse_title()
        self.description = self._parse_description()
        self.rationale = self._parse_rationale()
        self.impact = self._parse_impact()
        self.profile_applicability = self._parse_level()
        self.audit = self._parse_audit()
        self.remediation = self._parse_remediation()
        self.references = self._parse_references()
        self.default = self._parse_default()
        # TODO: Add support for 'CIS Controls' section

    def __dict__(self):
        return {
            'section': self.section,
            'title': self.title,
            'description': self.description,
            'default': self.default,
            'rationale': self.rationale,
            'impact': self.impact,
            'audit': self.audit,
            'remediation': self.remediation,
            'profile_applicability': self.profile_applicability}

    def _remove_newlines(self, string):
        return string.replace('\n', ' ')

    def _parse_description(self):
        pattern = re.compile(r"Description:[\w\s,/:.'-]*(?=Rationale:)")
        m = pattern.search(self._raw)
        if m:
            value = m[0].lstrip('Description:').lstrip().rstrip()
            return self._remove_newlines(value)

    def _parse_rationale(self):
        pattern = re.compile(r"Rationale:[\w\s\n.:/,'’()-]*(?=\sImpact:)")
        m = pattern.search(self._raw)
        if m:
            value = m[0].lstrip('Rationale:').lstrip().rstrip()
            value = self._remove_newlines(value)
            return self._remove_duplicate_spaces(value)

    def _parse_impact(self):
        pattern = re.compile(r'Impact:\s[\s\w\W]*?(?=Audit:)')
        m = pattern.search(self._raw)
        if m:
            value = self._remove_newlines(m[0])
            value = self._remove_page_numbers(value)
            value = self._remove_form_feed(value)
            value = self._remove_duplicate_spaces(value)
            value = value.lstrip('Impact:').lstrip().rstrip()
            if value == 'None' or value == 'None.':
                return None
            return value

    def _parse_section(self):
        pattern = re.compile(r'\d.\d.\d+')
        m = pattern.search(self._raw)
        if m:
            return m[0].lstrip().rstrip()

    def _parse_title(self):
        pattern = re.compile(r'\d.\d.\d+\s[\w\s():.-]*(?=Profile\sApplicability:)')
        m = pattern.search(self._raw)
        if m:
            value = self._remove_newlines(m[0])
            value = value.split(' ', maxsplit=1)[1]
            return value.lstrip().rstrip()

    def _parse_level(self):
        pattern = re.compile(r'Level \d')
        m = pattern.search(self._raw)
        if m:
            return m[0].lstrip().rstrip()

    def _parse_audit(self):
        pattern = re.compile(r'Audit:[\w \W \d \s()]*(?=Remediation:)')
        m = pattern.search(self._raw)
        if m:
            value = m[0]
            value = self._remove_page_numbers(value)
            value = self._remove_form_feed(value)
            value = value.lstrip('Audit: \n').rstrip()
            return value

    def _parse_remediation(self):
        pattern = re.compile(r'Remediation:[\w \W \d \s]*(?=Default\sValue:)')
        m = pattern.search(self._raw)
        if m:
            value = self._remove_page_numbers(m[0])
            value = self._remove_form_feed(value)
            return value.rstrip().lstrip('Remediation: \n')

    def _parse_references(self):
        pattern = re.compile(r'References:[\w \W \d \s]*(?=CIS\sControls:)')
        m = pattern.search(self._raw)
        if m:
            value = self._remove_form_feed(m[0])
            value = self._remove_page_numbers(value)
            return value.rstrip().lstrip('References: \n')

    def _parse_default(self):
        pattern = re.compile(r'Default\sValue:[\w \W \d \s]*(?=References:)')
        m = pattern.search(self._raw)
        if m:
            value = self._remove_newlines(m[0])
            value = self._remove_page_numbers(value)
            value = self._remove_form_feed(value)
            return value.rstrip().lstrip('Default Value: \n')

    def _remove_page_numbers(self, string):
        pattern = re.compile(r'\d+\s\|\sP\sa\sg\se')
        for match in pattern.findall(string):
            string = string.replace(match, '')
        return string

    def _remove_form_feed(self, string):
        return string.replace('\f', '')

    def _remove_duplicate_spaces(self, string):
        return re.sub(' +', ' ', string)


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


if __name__ == "__main__":
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
