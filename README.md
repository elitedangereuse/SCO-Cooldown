# SCO Cooldown — EDMC plugin

This lightweight EDMC plugin watches the `Status.json` payload received through
EDMC's `dashboard_entry` callback. It does not send journal or status data to
any server.

When Supercruise Overdrive (SCO) changes from active to inactive, the plugin
starts a countdown. Its progress bar fills in orange while the drive cools down,
then turns green and plays the bundled `sco_ready.wav` alert when SCO is ready.

The duration defaults to 9 seconds and can be changed in EDMC's plugin
settings. The same screen can test the alert and select a custom local sound
file; WAV is the most portable choice. SCO is detected from `Flags2` bit 20
(`0x00100000`), as documented in [the Elite Dangerous Status File reference](https://elite-journal.readthedocs.io/en/latest/Status%20File.html).

## FDev Issue Tracker reference

When this issue is fixed, this plugin will probably become useless:

https://issues.frontierstore.net/issue-detail/87980

## Installation

Please follow the updated instructions here:

https://github.com/EDCD/EDMarketConnector/wiki/Plugins
