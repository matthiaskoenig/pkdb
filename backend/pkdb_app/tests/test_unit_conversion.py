from collections import namedtuple

from django.test import TestCase
from pkdb_app.units import UNIT_CONVERSIONS, UnitConversion, UNIT_CONVERSIONS_DICT

Measurement = namedtuple('Measurement',["value","unit"])
Transform = namedtuple('Transform',["input","output"])

test_data = [
    Transform(input=Measurement(80,"kg"),output=Measurement(80000,"g")),
    Transform(input=Measurement(180, "cm"), output=Measurement(1.8, "m")),
    Transform(input=Measurement(1000, "ml"), output=Measurement(1, "l")),
    Transform(input=Measurement(60, "min"), output=Measurement(1, "h")),
    Transform(input=Measurement(1, "1/min"), output=Measurement(60, "1/h")),
    # Concentrations
    Transform(input=Measurement(1, "mg/dl"), output=Measurement(10, "µg/ml")),
    Transform(input=Measurement(1, "mg/l"), output=Measurement(1, "µg/ml")),
    Transform(input=Measurement(1, "g/dl"), output=Measurement(10000, "µg/ml")),
    Transform(input=Measurement(1, "ng/ml"), output=Measurement(0.001, "µg/ml")),
    Transform(input=Measurement(1, "ng/ml"), output=Measurement(0.001, "µg/ml")),
    # AUC
    Transform(input=Measurement(1, "µg*h/ml"), output=Measurement(1, "mg*h/l")),
    Transform(input=Measurement(60, "µg*min/ml"), output=Measurement(1, "mg*h/l")),
    Transform(input=Measurement(1, "µg/ml*h/kg"), output=Measurement(1, "mg*h/l/kg")),

    # Vd
    Transform(input=Measurement(1, "ml/kg"), output=Measurement(0.001, "l/kg")),
    # clearance
    Transform(input=Measurement(1, "ml/h/kg"), output=Measurement(0.001, "l/h/kg")),
    Transform(input=Measurement(1, "ml/min/kg"), output=Measurement(0.06, "l/h/kg")),
    Transform(input=Measurement(1, "ml/min"), output=Measurement(0.06, "l/h")),
    Transform(input=Measurement(100, "%"), output=Measurement(1, "-")),

]

class TestUnitConversion(TestCase):

    def test_conversions(self):
        for transform in test_data:
            value = transform.input.value
            unit = transform.input.unit
            norm_value = transform.output.value
            norm_unit = transform.output.unit

            conversion_key = f"[{unit}] -> [{norm_unit}]"
            conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
            self.assertTrue(conversion, msg=f"conversion{conversion_key} does not exist")

            calculated_value = conversion.apply_conversion(value)

            self.assertEqual(calculated_value,norm_value, msg=f"For conversion {conversion_key}")




