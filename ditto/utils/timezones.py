import zoneinfo


__all__ = (
    "MAIN_TIMEZONES",
    "TIMEZONE_ALIASES",
)


MAIN_TZ_FILE = "res/cldr/tools/cldr-code/src/main/resources/org/unicode/cldr/util/MainTimeZones.txt"
TZ_ALIASES_FILE = "res/cldr/tools/cldr-code/src/main/resources/org/unicode/cldr/util/data/TimeZoneAliases.txt"

# ALL_TIMEZONES: list[str] = []

MAIN_TIMEZONES: dict[str, zoneinfo.ZoneInfo] = {}

TIMEZONE_ALIASES: dict[str, str] = {}

with open(TZ_ALIASES_FILE) as f:
    for record in f:
        if record.strip() and not record.startswith("#"):
            alias, key = (timezone.strip() for timezone in record.split(";", 1))

            try:
                tzinfo = zoneinfo.ZoneInfo(key)
            except:
                continue

            TIMEZONE_ALIASES[alias] = key

            # Skip some specific timezones
            if alias.startswith("SystemV") or any(c.isdigit() for c in alias):
                continue

            MAIN_TIMEZONES[alias] = tzinfo
