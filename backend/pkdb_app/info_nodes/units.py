import pint

ureg = pint.UnitRegistry()

# Units
ureg.define('cups = count')
ureg.define('beverages = count')
ureg.define('none = count')
ureg.define('percent = 0.01*count')
ureg.define('IU = [activity_amount]')
ureg.define('NO_UNIT = [no_unit]')
