import os
import unittest

import ddt

import bp

PDF_FILE = os.getenv('CONTROL_PDF', False)
ASSERTION_FILE = os.getenv('ASSERTION_FILE', False)

# FIXME: This is a workaround for cases where unit tests are invoked without
# necessary inputs, like a PDF to parse and the assertions in yaml format to
# load with DDT. The reason why this is here instead of encoded in custom a
# decorator is because the decorators will get initialized during test
# discovery, and we can't call ddt.file_data() without a valid file. In other
# words, even if we attempt to skip the test when ASSERTION_FILE='' or is
# unset, ddt.file_data() will still raise an exception, regardless of how we
# nest the decorators.
if not (PDF_FILE and ASSERTION_FILE):
    raise unittest.SkipTest('CONTROL_PDF and/or ASSERTION_FILE are not set')
        

@ddt.ddt
class ControlTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # The to_dict() method returns a dictionary, where the key is the
        # section (e.g., 1.1.1) and the value is an instance of Control. All
        # the Control instances reference the same underlying raw data, but
        # they don't change any of the data. The Control uses new strings for
        # any mutable changes (which makes sense because strings are
        # immutable). This should be safe to use across test cases and results
        # in faster test runs since we're only converting the PDF once and
        # building the Control objects once.
        benchmark_pdf_file = os.path.abspath(PDF_FILE)
        raw_text = bp.convert_pdf(benchmark_pdf_file)
        cls.controls = bp.to_dict(raw_text)

    def setUp(self):
        self.maxDiff = None

    @ddt.file_data(os.path.abspath(ASSERTION_FILE))
    def test_section(self, **kwargs):
        section = kwargs.pop('section')
        title = kwargs.pop('title')
        profile_applicability = kwargs.pop('profile_applicability')
        description = kwargs.pop('description')
        rationale = kwargs.pop('rationale')
        impact = kwargs.pop('impact')
        audit = kwargs.pop('audit')
        remediation = kwargs.pop('remediation')
        default = kwargs.pop('default')
        references = kwargs.pop('references')

        control = self.controls[section]
        self.assertEqual(control.section, section)
        self.assertEqual(control.title, title)
        self.assertEqual(control.profile_applicability, profile_applicability)
        self.assertEqual(control.description, description)
        self.assertEqual(control.rationale, rationale)
        self.assertEqual(control.impact, impact)
        self.assertEqual(control.audit, audit)
        self.assertEqual(control.remediation, remediation)
        self.assertEqual(control.default, default)
        self.assertEqual(control.references, references)
