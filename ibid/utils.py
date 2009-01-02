
def ago(delta, units=None):
	parts = []

	for unit, value in (('year', delta.days/365), ('month', delta.days/30 % 12), ('day', delta.days % 30), ('hour', delta.seconds/3600), ('minute', delta.seconds/60 % 60), ('second', delta.seconds % 60), ('millisecond', delta.microseconds/1000)):
		if value > 0 and (unit != 'millisecond' or len(parts) == 0):
			parts.append('%s %s%s' % (value, unit, value != 1 and 's' or ''))
			if units and len(parts) >= units:
				break

	formatted =  ' and '.join(parts)
	return formatted.replace(' and ', ', ', len(parts)-2)
