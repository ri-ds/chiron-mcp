from django.test import TestCase
from chiron.helpers import age_in_days_to_years_days


class HelpersTest(TestCase):
    def test_age_in_days_to_years_days(self):
        self.assertEqual((0, 1), age_in_days_to_years_days(1))
        self.assertEqual((1, 0), age_in_days_to_years_days(365))
        self.assertEqual((1, 1), age_in_days_to_years_days(366))
        self.assertEqual((0, -1), age_in_days_to_years_days(-1))
        self.assertEqual((-1, 0), age_in_days_to_years_days(-365))
        self.assertEqual((-1, -1), age_in_days_to_years_days(-366))
