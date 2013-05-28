#!/usr/bin/env python3

# ranwhen – Visualize when your system was running
#
# Requirements:
# - *nix system with last(1) installed and supporting the -R and -F flags
# - Python >= 3.2
# - Terminal emulator with support for Unicode and xterm's 256 color mode
#
#
# Copyright © 2013 Philipp Emanuel Weidmann <pew@worldwidemann.com>
#
# Nemo vir est qui mundum non reddat meliorem.
#
#
# ranwhen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ranwhen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ranwhen.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import re
from datetime import datetime, timedelta
import sys


# Line format of last's output
# e.g. "reboot   system boot  Wed Jan 16 21:36:54 2013 - Wed Jan 16 22:05:50 2013  (00:28)"
line_pattern = re.compile("reboot\s+system\s+boot\s+\w{3}\s+([\d\w\s:]{20})\s+-\s+\w{3}\s+([\d\w\s:]{20})")

# Date format used by last
# e.g. "Jan 16 21:36:54 2013"
time_format = "%b %d %H:%M:%S %Y"

# Extracts start and end time from a line of last's output
def parse_line(line):
	result = line_pattern.match(line)
	if result is None:
		return None
	else:
		from_time = datetime.strptime(result.group(1), time_format)
		to_time   = datetime.strptime(result.group(2), time_format)
		return { "from" : from_time, "to" : to_time }


# Returns the length of time for which two time spans overlap
# (i.e. the length of their intersection)
def time_overlap(time_span_1, time_span_2):
	if max(time_span_1["from"], time_span_2["from"]) >= \
	   min(time_span_1["to"], time_span_2["to"]):
		# No overlap
		return timedelta()
	return min(time_span_1["to"], time_span_2["to"]) - \
	       max(time_span_1["from"], time_span_2["from"])


# Do not use escape sequences if output is piped
use_escape_sequences = sys.stdout.isatty()

# Returns an xterm escape sequence that, if printed to the terminal,
# will reset all character attributes to the default
def get_reset_sequence():
	if use_escape_sequences:
		return "\033[0m"
	return ""

# Returns an xterm escape sequence that, if printed to the terminal,
# will set the specified character attributes
def get_escape_sequence(fgcolor = None, bgcolor = None, bold = False):
	if use_escape_sequences:
		return get_reset_sequence() + \
		       "\033[%s%s%sm" % \
		       ("" if fgcolor is None else ("38;5;%d" % fgcolor), \
		       	"" if bgcolor is None else (";48;5;%d" % bgcolor), \
		       	";1" if bold else "")
	return ""

# Output colors as xterm color codes
# (see e.g. http://www.calmar.ws/vim/256-xterm-24bit-rgb-color-chart.html)
foreground_color = 251
heading_color = 208
heading_line_color = 246
time_color = 231
time_text_color = 246
histogram_color = [ 57, 56, 126, 197 ]
histogram_color_grid = [ 99, 97, 169, 204 ]
weekday_color = 245
weekend_color = 231
bar_color = 28
bar_weekend_color = 82
bar_color_grid = 77
bar_weekend_color_grid = 156
night_color = 51
sunrise_color = 228
noon_color = 226
sunset_color = 214
grid_color = 238

# Returns a string that, if printed to the terminal,
# will display the specified text with the specified attributes
def style_text(text, fgcolor = foreground_color, bgcolor = None, bold = False):
	return get_escape_sequence(fgcolor, bgcolor, bold) + text + \
	       get_escape_sequence(fgcolor = foreground_color)


# Computes the number of hours (total), minutes and seconds
# in the specified timedelta object
def get_delta_fields(delta):
	fields = {}
	fields["hours"], remainder = divmod(round(delta.total_seconds()), 3600)
	fields["minutes"], fields["seconds"] = divmod(remainder, 60)
	return fields

# Formats the specified timedelta object into a string
# of the form "X hours Y minutes"
def format_delta(delta):
	fields = get_delta_fields(delta)
	return style_text("%4d" % fields["hours"], fgcolor = time_color) + \
	       style_text(" hours ", fgcolor = time_text_color) + \
	       style_text("%2d" % fields["minutes"], fgcolor = time_color) + \
	       style_text(" minutes", fgcolor = time_text_color)

# Formats the specified timedelta object into a string
# of the form "XX:YY"
def format_delta_short(delta):
	fields = get_delta_fields(delta)
	if fields["hours"] == 0 and fields["minutes"] == 0:
		return ""
	if fields["hours"] == 0:
		return style_text("  :", fgcolor = time_text_color) + \
		       style_text("%02d" % fields["minutes"], fgcolor = time_color)
	return style_text("%2d" % fields["hours"], fgcolor = time_color) + \
	       style_text(":", fgcolor = time_text_color) + \
		   style_text("%02d" % fields["minutes"], fgcolor = time_color)

output_width = 61

# Returns a styled section separator used to frame a calendar month
def format_heading(heading):
	padded_heading = " " + heading + " "
	heading_pos = int((output_width - len(padded_heading)) / 2)
	full_heading = style_text("┌" + ("─" * heading_pos), fgcolor = heading_line_color) + \
	               style_text(padded_heading, fgcolor = heading_color)
	full_heading += style_text(("─" * (output_width - heading_pos - len(padded_heading))) + "┐", \
		                       fgcolor = heading_line_color)
	return full_heading



##### Program logic starts here #####



# ranwhen parses the output of this command
command = "last -R -F reboot"


# Major time granularity (lines)
day = timedelta(days = 1)

# Minor time granularity (columns)
half_hour = timedelta(minutes = 30)

# Ratio of granularities (columns per line)
half_hours_in_day = round(day / half_hour)


output = subprocess.check_output(command.split(), universal_newlines = True)

lines = output.splitlines()

time_spans = []

### Parse output
for line in lines:
	result = parse_line(line)
	if result is not None:
		time_spans.append(result)

if not time_spans:
	sys.exit("Error: '%s' returned no parsable output" % command)


### Merge overlapping time spans (for unknown reasons, last sometimes outputs them)
time_spans_merged = True
while time_spans_merged:
	time_spans_merged = False
	time_spans_new = []
	i = 0
	while i < len(time_spans):
		if i < len(time_spans) - 1 and time_overlap(time_spans[i], time_spans[i + 1]) > timedelta():
			# Time spans overlap
			time_spans_new.append({ "from" : min(time_spans[i]["from"], time_spans[i + 1]["from"]), \
			                        "to"   : max(time_spans[i]["to"], time_spans[i + 1]["to"]) })
			i += 1
			time_spans_merged = True
		else:
			time_spans_new.append(time_spans[i])
		i += 1
	time_spans = time_spans_new


### Compute period
latest_time   = time_spans[0]["to"]
earliest_time = time_spans[-1]["from"]

latest_time   = latest_time.replace(hour = 0, minute = 0, second = 0) + day
earliest_time = earliest_time.replace(hour = 0, minute = 0, second = 0)


### Compute runtime for each half hour time slot in period
time_slots = []

aggregated_time_slots = [ timedelta() ] * half_hours_in_day

total_time = timedelta()

current_time = latest_time
while current_time > earliest_time:
	current_time -= half_hour
	time_slot = { "from" : current_time, "to" : current_time + half_hour }
	time_in_slot = timedelta()
	for time_span in time_spans:
		time_in_slot += time_overlap(time_slot, time_span)
	time_slots.append({ "time" : current_time, "time_in_slot" : time_in_slot })
	half_hour_index = current_time.hour * 2 + (1 if current_time.minute >= 30 else 0)
	aggregated_time_slots[half_hour_index] += time_in_slot
	total_time += time_in_slot


# Required because we want to process the individual days from the start of each one
time_slots.reverse()


time_header = "       0:00 " + style_text("☾", fgcolor = night_color) + \
			  "      6:00 " + style_text("☀", fgcolor = sunrise_color) + \
			  "     12:00 " + style_text("☀", fgcolor = noon_color) + \
			  "     18:00 " + style_text("☀", fgcolor = sunset_color) + \
			  "     24:00 " + style_text("☽", fgcolor = night_color)

grid_header = style_text("▆           ▆           ▆           ▆           ▆", fgcolor = grid_color)
grid_footer = style_text("▀           ▀           ▀           ▀           ▀", fgcolor = grid_color)

level_characters = [ " ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█" ]


# Set default foreground color for output
print(get_escape_sequence(fgcolor = foreground_color), end = "")


### Print summary
number_of_days = (latest_time - earliest_time).days

print(style_text("Period:  ", bold = True) + \
	  earliest_time.strftime("%B %d %Y") + " – " + \
	  (latest_time - day).strftime("%B %d %Y") + \
	  " (" + \
	  style_text("%d" % number_of_days, fgcolor = time_color) + \
	  style_text(" days", fgcolor = time_text_color) + ")")

print()

print(style_text("Total time running: ", bold = True) + format_delta(total_time))
print(style_text("Daily average:      ", bold = True) + format_delta(total_time / number_of_days))

print()
print()


### Print histogram
print(style_text("Histogram:", bold = True))
print()
print(time_header)
print("   max  " + grid_header)

number_of_lines = 4

levels = len(level_characters) - 1

min_level = (min(aggregated_time_slots) / number_of_days) / half_hour
max_level = (max(aggregated_time_slots) / number_of_days) / half_hour

def format_histogram_line(label, index):
	line = label + "  "
	slot_index = 0
	for time_slot in aggregated_time_slots:
		level = (time_slot / number_of_days) / half_hour
		# Normalize level to increase resolution
		level = (level - min_level) / (max_level - min_level)
		level = round(level * (levels * number_of_lines)) - (index * levels)
		# Clamp level to permissible range
		level = max(0, min(levels, level))
		grid = slot_index % 12 == 0
		slot_index += 1
		line += style_text(level_characters[level], \
			               fgcolor = histogram_color_grid[index] if grid else histogram_color[index],
			               bgcolor = grid_color if grid else None)
	line += style_text(" ", bgcolor = grid_color)
	return line

print(format_histogram_line("      ", 3))
print(format_histogram_line("      ", 2))
print(format_histogram_line("      ", 1))
print(format_histogram_line("   min", 0))

print("        " + grid_footer)

print()


### Print month views
current_time = latest_time

# 0 is not a valid month index, so the "month changed" condition
# will always be fulfilled in the first iteration
current_month = 0

# Do not use full block character here to keep separation between lines
levels = len(level_characters) - 2

while current_time > earliest_time:
	current_time -= day

	month_changed = current_time.month != current_month

	if month_changed:
		current_month = current_time.month
		print()
		print()
		print(format_heading(current_time.strftime("%B %Y")))
		print()
		print(time_header)
		print("        " + grid_header)

	weekend = current_time.weekday() in [5, 6]
	sunday  = current_time.weekday() == 6

	time_text = style_text(current_time.strftime("%a"), \
		                   fgcolor = weekend_color if weekend else weekday_color, \
		                   bold = sunday)
	time_text += current_time.strftime(" %d").replace(" 0", "  ")

	output_line = time_text + "  "

	time_sum = timedelta()

	bar_text = ""

	slot_index = 0

	### Build chart for day
	for time_slot in time_slots:
		if time_slot["time"] >= current_time and time_slot["time"] < current_time + day:
			time_sum += time_slot["time_in_slot"]
			level = round((time_slot["time_in_slot"] / half_hour) * levels)
			grid = slot_index % 12 == 0
			slot_index += 1
			bar_text += style_text(level_characters[level], \
				                   fgcolor = (bar_weekend_color_grid if grid else bar_weekend_color) if weekend \
				                             else (bar_color_grid if grid else bar_color),
				                   bgcolor = grid_color if grid else None)

	output_line += bar_text

	output_line += style_text(" ", bgcolor = grid_color)

	output_line += " " + format_delta_short(time_sum)

	print(output_line)

	if (current_time.day == 1) or \
	   (current_time <= earliest_time):
		# End of month
		print("        " + grid_footer)


# Reset text attributes
print(get_reset_sequence(), end = "")
