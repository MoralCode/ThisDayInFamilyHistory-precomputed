import sys
from datetime import date
from collections import defaultdict
import os
from pathlib import Path



# Add the Gramps source directory to the path if not already there.
# This might need to be adjusted based on your Gramps installation.



# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Assuming 'gramps_src' is the submodule directory name
GRAMPS_INSTALL_PATH = Path(sys.argv[1])

if not os.path.exists(GRAMPS_INSTALL_PATH):
	print(f"Error: Gramps submodule not found at {GRAMPS_INSTALL_PATH}")
	print("Please ensure the submodule is correctly initialized and updated.")
	sys.exit(1)

if GRAMPS_INSTALL_PATH not in sys.path:
	sys.path.insert(0, GRAMPS_INSTALL_PATH)



# try:
from gramps.gen.dbstate import DbState
from gramps.cli.grampscli import CLIManager
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import Person, FamilyRelType
from gramps.gen.lib.date import Date
# except ImportError as e:
#     print(
#         "Error: Gramps modules not found. "
#         "Please ensure the Gramps source directory is in your Python path."
#     )
#     print(
#         "You might need to add it using sys.path.append('/path/to/gramps_src')"
#     )
#     print(e)
#     sys.exit(1)

# Internationalisation
try:
	_trans = glocale.get_addon_translator(__file__)
except ValueError:
	_trans = glocale.translation
_ = _trans.gettext


class ThisDayInFamilyHistoryGenerator:
	__UNSUPPORTED_EVENTS = [
		'Alternate Parentage',
		'Cause Of Death',
		'Education',
		'Medical Information',
		'Number of Marriages',
		'Occupation',
		'Property',
		'Religion',
		'Residence',
		'Will',
		'Year',
	]

	# These are the events we want to specifically track for "this day"
	# For a website, we might want to be more selective than the Gramplet's
	# default choices, especially for deceased individuals.
	# I've started with a reasonable subset based on the Gramplet's defaults.
	__EVENTS_TO_REPORT = [
		'Adopted',
		'Adult Christening',
		'Birth',
		'Death',
		'Elected',
		'Emigration',
		'Graduation',
		'Immigration',
		'Marriage',
		'Military Service',
		'Naturalization',
		'Nobility Title',
		'Ordination',
		'Retirement',
		'Burial',  # Added burial for deceased context
		'Cremation',  # Added cremation for deceased context
	]

	# --- Event message templates from the original gramplet, adapted for
	#     standalone use ---
	__EVENT_MESSAGE = {}
	__EVENT_MESSAGE['adopted'] = {
		'male': _("%(male_name)s was adopted in %(year)s at %(place)s."),
		'female': _("%(female_name)s was adopted in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['adult christening'] = {
		'male': _("%(male_name)s was christened in %(year)s at %(place)s."),
		'female': _("%(female_name)s was christened in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['alternate marriage'] = {
		'male': _("%(male_name)s was married in %(year)s at %(place)s."),
		'female': _("%(female_name)s was married in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['annulment'] = {
		'male': _("%(male_name)s received an annulment in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s received an annulment in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['baptism'] = {
		'male': _("%(male_name)s was baptized in %(year)s at %(place)s."),
		'female': _("%(female_name)s was baptized in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['bar mitzvah'] = {
		'male': _("%(male_name)s became a bar mitzvah in %(year)s at %(place)s."),
		'female': _("%(female_name)s became a bar mitzvah in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['bat mitzvah'] = {
		'male': _("%(male_name)s became a bat mitzvah in %(year)s at %(place)s."),
		'female': _("%(female_name)s became a bat mitzvah in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['birth'] = {
		'male': _("%(male_name)s was born in %(year)s at %(place)s."),
		'female': _("%(female_name)s was born in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['blessing'] = {
		'male': _("%(male_name)s was blessed in %(year)s at %(place)s."),
		'female': _("%(female_name)s was blessed in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['burial'] = {
		'male': _("%(male_name)s was buried in %(year)s at %(place)s."),
		'female': _("%(female_name)s was buried in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['census'] = {
		'male': _(
			"%(male_name)s participated in a census in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s participated in a census in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['christening'] = {
		'male': _("%(male_name)s was christened in %(year)s at %(place)s."),
		'female': _("%(female_name)s was christened in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['confirmation'] = {
		'male': _("%(male_name)s was confirmed in %(year)s at %(place)s."),
		'female': _("%(female_name)s was confirmed in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['cremation'] = {
		'male': _("%(male_name)s was cremated in %(year)s at %(place)s."),
		'female': _("%(female_name)s was cremated in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['death'] = {
		'male': _("%(male_name)s died in %(year)s at %(place)s."),
		'female': _("%(female_name)s died in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['degree'] = {
		'male': _("%(male_name)s was awarded a degree in %(year)s at %(place)s."),
		'female': _("%(female_name)s was awarded a degree in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['divorce'] = {
		'male': _("%(male_name)s was granted a divorce in %(year)s at " "%(place)s."),
		'female': _(
			"%(female_name)s was granted a divorce in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['divorce filing'] = {
		'male': _("%(male_name)s filed for divorce in %(year)s at %(place)s."),
		'female': _("%(female_name)s filed for divorce in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['elected'] = {
		'male': _("%(male_name)s was elected in %(year)s at %(place)s."),
		'female': _("%(female_name)s was elected in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['emigration'] = {
		'male': _("%(male_name)s emigrated in %(year)s at %(place)s."),
		'female': _("%(female_name)s emigrated in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['engagement'] = {
		'male': _("%(male_name)s became engaged in %(year)s at %(place)s."),
		'female': _("%(female_name)s became engaged in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['first communion'] = {
		'male': _(
			"%(male_name)s received first communion in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s received first communion in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['graduation'] = {
		'male': _("%(male_name)s graduated in %(year)s at %(place)s."),
		'female': _("%(female_name)s graduated in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['immigration'] = {
		'male': _("%(male_name)s immigrated in %(year)s at %(place)s."),
		'female': _("%(female_name)s immigrated in %(year)s at %(place)s."),
	}

	# Marriage event types
	__EVENT_MESSAGE['marriage' + str(FamilyRelType.MARRIED)] = {
		'male': _("%(male_name)s got married in %(year)s at %(place)s."),
		'female': _("%(female_name)s got married in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['marriage' + str(FamilyRelType.UNMARRIED)] = {
		'male': _("%(male_name)s joined as a family in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s joined as a family in %(year)s at %(place)s."
		),
	}
	__EVENT_MESSAGE['marriage' + str(FamilyRelType.CIVIL_UNION)] = {
		'male': _(
			"%(male_name)s entered a civil union in %(year)s at %(place)s."
		),
		'female': _(
			"%(female_name)s entered a civil union in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['marriage' + str(FamilyRelType.UNKNOWN)] = {
		'male': _("%(male_name)s joined as a family in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s joined as a family in %(year)s at %(place)s."
		),
	}
	__EVENT_MESSAGE['marriage' + str(FamilyRelType.CUSTOM)] = {
		'male': _(
			"%(male_name)s had a custom marriage in %(year)s at %(place)s."
		),
		'female': _(
			"%(female_name)s had a custom marriage in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['marriage banns'] = {
		'male': _(
			"%(male_name)s announced a marriage banns in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s announced a marriage banns in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['marriage contract'] = {
		'male': _(
			"%(male_name)s entered a marriage contract in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s entered a marriage contract in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['marriage license'] = {
		'male': _(
			"%(male_name)s obtained a marriage license in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s obtained a marriage license in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['marriage settlement'] = {
		'male': _(
			"%(male_name)s obtained a marriage settlement in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s obtained a marriage settlement in %(year)s "
			"at %(place)s."
		),
	}
	__EVENT_MESSAGE['military service'] = {
		'male': _(
			"%(male_name)s entered military service in %(year)s at "
			"%(place)s."
		),
		'female': _(
			"%(female_name)s entered military service in %(year)s at "
			"%(place)s."
		),
	}
	__EVENT_MESSAGE['naturalization'] = {
		'male': _("%(male_name)s became naturalized in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s became naturalized in %(year)s at %(place)s."
		),
	}
	__EVENT_MESSAGE['nobility title'] = {
		'male': _("%(male_name)s had a title bestowed in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s had a title bestowed in %(year)s at %(place)s."
		),
	}
	__EVENT_MESSAGE['ordination'] = {
		'male': _("%(male_name)s was ordained in %(year)s at %(place)s."),
		'female': _("%(female_name)s was ordained in %(year)s at %(place)s."),
	}
	__EVENT_MESSAGE['probate'] = {
		'male': _("%(male_name)s was granted probate in %(year)s at %(place)s."),
		'female': _(
			"%(female_name)s was granted probate in %(year)s at %(place)s."
		),
	}
	__EVENT_MESSAGE['retirement'] = {
		'male': _("%(male_name)s retired in %(year)s at %(place)s."),
		'female': _("%(female_name)s retired in %(year)s at %(place)s."),
	}

	def __init__(self, db_path):
		self.db_path = db_path
		self.dbstate = DbState()
		self.dbman = CLIManager(self.dbstate, True, None)
	
		self.dbman.do_reg_plugins(self.dbstate, uistate=None)
	    # reload_custom_filters()
		self.dbman.open_activate(db_path)
		self.db = self.dbstate.db
		self.deceased_person_gids = set()
		self.events_by_day = defaultdict(list)

	def connect_db(self):
		"""Connects to the Gramps database."""
		try:
			self.db.open(self.db_path)
			print(f"Successfully connected to Gramps database: {self.db_path}")
		except Exception as e:
			print(f"Error connecting to Gramps database: {e}")
			sys.exit(1)

	def close_db(self):
		"""Closes the Gramps database connection."""
		self.db.close()
		print("Gramps database connection closed.")

	def _is_person_deceased(self, person):
		"""Checks if a person has a death or burial event."""
		for ref in person.get_event_ref_list():
			event = self.db.get_event_from_handle(ref.ref)
			e_type = event.get_type().xml_str().lower()
			if e_type in ['death', 'burial', 'cremation']:
				return True
		return False

	def _get_place_name(self, event):
		"""Extracts the primary place name for an event."""
		for r in event.get_referenced_handles():
			if r[0] == 'Place':  # r[0] is the type, r[1] is the handle
				place = self.db.get_place_from_handle(r[1])
				return place.get_name().get_value()
		return _('unknown location')

	def _get_person_event_data(self, person, event, e_date):
		"""Extracts and formats data for a person event."""
		e_type = event.get_type().xml_str()
		if e_type in self.__UNSUPPORTED_EVENTS or e_type not in self.__EVENTS_TO_REPORT:
			return None

		name = person.get_primary_name().get_regular_name()
		gramps_id = person.serialize()[1]
		gender = person.get_gender()
		year = e_date.get_year() or _("unknown")
		place = self._get_place_name(event)

		extra_info = ''
		if e_type.lower() == 'marriage':
			# For person-centric marriage events, we often don't have
			# FamilyRelType directly associated. We'll use UNKNOWN for now
			# as a placeholder if not linked to a family.
			extra_info = int(FamilyRelType.UNKNOWN)

		return {
			'name': name,
			'gramps_id': gramps_id,
			'gender': gender,
			'event_type': e_type,
			'year': year,
			'place': place,
			'extra_info': extra_info,
			'handle': person.handle,  # For potential future linking
			'handle_type': _('Person'),
		}

	def _get_family_event_data(self, family, event, e_date):
		"""Extracts and formats data for a family event."""
		e_type = event.get_type().xml_str()
		if e_type in self.__UNSUPPORTED_EVENTS or e_type not in self.__EVENTS_TO_REPORT:
			return None

		father_handle = family.get_father_handle()
		mother_handle = family.get_mother_handle()

		father = (
			self.db.get_person_from_handle(father_handle)
			if father_handle
			else None
		)
		mother = (
			self.db.get_person_from_handle(mother_handle)
			if mother_handle
			else None
		)

		father_name = (
			father.get_primary_name().get_regular_name()
			if father
			else _('Unknown Father')
		)
		mother_name = (
			mother.get_primary_name().get_regular_name()
			if mother
			else _('Unknown Mother')
		)

		# Check if both partners are deceased
		is_father_deceased = father and (father.serialize()[1] in self.deceased_person_gids)
		is_mother_deceased = mother and (mother.serialize()[1] in self.deceased_person_gids)

		if not (is_father_deceased and is_mother_deceased):
			return None  # Only report family events where *both* are deceased

		name = f"{father_name} and {mother_name}"
		gramps_id = f"{father.serialize()[1] if father else ''}-" \
					f"{mother.serialize()[1] if mother else ''}"
		gender = Person.UNKNOWN  # Family events don't have a single gender
		year = e_date.get_year() or _("unknown")
		place = self._get_place_name(event)
		extra_info = int(family.get_relationship())

		return {
			'name': name,
			'gramps_id': gramps_id,
			'gender': gender,
			'event_type': e_type,
			'year': year,
			'place': place,
			'extra_info': extra_info,
			'handle': family.handle,  # For potential future linking
			'handle_type': _('Family'),
		}

	def generate_events_for_deceased(self):
		"""
		Iterates through the database to find events for deceased individuals
		and categorizes them by day and month.
		"""
		print("Identifying deceased individuals...")
		# First pass: identify all deceased persons by Gramps ID
		for person in self.db.iter_people():
			if self._is_person_deceased(person):
				self.deceased_person_gids.add(person.serialize()[1])

		print(f"Found {len(self.deceased_person_gids)} deceased individuals.")
		print("Collecting events for deceased individuals and their families...")

		# Second pass: collect events for deceased persons
		for person in self.db.iter_people():
			person_gid = person.serialize()[1]
			if person_gid in self.deceased_person_gids:
				for ref in person.get_event_ref_list():
					event = self.db.get_event_from_handle(ref.ref)
					e_date = event.get_date_object()

					if not e_date.is_valid():
						continue

					# Convert to Gregorian for consistent date matching
					if e_date.get_calendar() != Date.CAL_GREGORIAN:
						e_date = e_date.to_calendar('gregorian')

					e_day = e_date.get_day()
					e_month = e_date.get_month()

					if e_day and e_month:  # Ensure day and month are known
						event_data = self._get_person_event_data(
							person, event, e_date
						)
						if event_data:
							day_key = (e_month, e_day)
							self.events_by_day[day_key].append(event_data)

		# Third pass: collect events for families where *both* partners are deceased
		for family in self.db.iter_families():
			father_handle = family.get_father_handle()
			mother_handle = family.get_mother_handle()

			father_gid = (
				self.db.get_person_from_handle(father_handle).serialize()[1]
				if father_handle
				else None
			)
			mother_gid = (
				self.db.get_person_from_handle(mother_handle).serialize()[1]
				if mother_handle
				else None
			)

			# Only consider family events if both partners are deceased.
			# If one or both are unknown, we don't include it in this specific
			# "deceased individuals only" report.
			if father_gid in self.deceased_person_gids and \
			mother_gid in self.deceased_person_gids:
				for ref in family.get_event_ref_list():
					event = self.db.get_event_from_handle(ref.ref)
					e_date = event.get_date_object()

					if not e_date.is_valid():
						continue

					if e_date.get_calendar() != Date.CAL_GREGORIAN:
						e_date = e_date.to_calendar('gregorian')

					e_day = e_date.get_day()
					e_month = e_date.get_month()

					if e_day and e_month:
						event_data = self._get_family_event_data(
							family, event, e_date
						)
						if event_data:
							day_key = (e_month, e_day)
							self.events_by_day[day_key].append(event_data)

		print("Finished collecting events.")

	def format_event_message(self, event_data):
		"""Formats a single event into a human-readable string."""
		e_str = event_data['event_type'].lower()
		year = event_data['year']
		place = event_data['place']
		name = event_data['name']
		gender = event_data['gender']
		extra_info = event_data['extra_info']

		# Handle marriage events with specific relationship types
		if e_str == 'marriage':
			e_str = e_str + str(extra_info)

		# Default to male message if gender is unknown or not applicable
		msg_template = None
		if gender == Person.FEMALE:
			msg_template = self.__EVENT_MESSAGE.get(e_str, {}).get('female')
		if not msg_template:  # Fallback to male if female not found or default
			msg_template = self.__EVENT_MESSAGE.get(e_str, {}).get('male')

		if not msg_template:
			# Fallback if no specific message template exists
			return _(
				f"{name} experienced a {event_data['event_type']} event "
				f"in {year} at {place}."
			)

		# Use the appropriate placeholder for the name
		if gender == Person.FEMALE and '%(female_name)s' in msg_template:
			formatted_message = msg_template % {
				'female_name': name,
				'year': year,
				'place': place,
			}
		else:
			formatted_message = msg_template % {
				'male_name': name,
				'year': year,
				'place': place,
			}
		return formatted_message

	def export_daily_events_for_website(self, output_dir="daily_events"):
		"""
		Exports the collected daily events into a format suitable for a website.
		Creates a JSON file for each day.
		"""
		import os
		import json

		os.makedirs(output_dir, exist_ok=True)
		print(f"\nExporting daily events to {output_dir}/")

		for month in range(1, 13):
			for day in range(1, 32):  # Iterate through all possible days
				try:
					# Validate day for the month (e.g., Feb 30 is invalid)
					date(2000, month, day)  # Use a leap year for Feb 29
				except ValueError:
					continue  # Skip invalid dates

				day_key = (month, day)
				events_for_day = self.events_by_day.get(day_key, [])

				output_list = []
				for event in events_for_day:
					formatted_desc = self.format_event_message(event)
					output_list.append({
						'person_name': event['name'],
						'gramps_id': event['gramps_id'],
						'event_type': event['event_type'],
						'year': event['year'],
						'place': event['place'],
						'description': formatted_desc,
						'handle_type': event['handle_type'],
						# Add handle for direct link if website supports it
						'handle': str(event['handle']),
					})

				if output_list: # Only create files for days with events
					filename = f"events_{month:02d}_{day:02d}.json"
					filepath = os.path.join(output_dir, filename)
					with open(filepath, 'w', encoding='utf-8') as f:
						json.dump(output_list, f, ensure_ascii=False, indent=2)
					print(f"  Created {filename} with {len(output_list)} events.")
				# else:
				#     print(f"  No events for {month:02d}/{day:02d}.")

		print("Export complete.")

	def run(self, output_dir="daily_events"):
		# self.connect_db()
		self.generate_events_for_deceased()
		self.export_daily_events_for_website(output_dir)
		self.close_db()


if __name__ == "__main__":

	generator = ThisDayInFamilyHistoryGenerator(sys.argv[2])
	generator.run()