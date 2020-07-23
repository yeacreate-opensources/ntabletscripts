# NTablet Scripts #

The scripts in this directory need the websockets python package to be
installed.
The NTablet uses digest authorisation so the pull request
https://github.com/aaugustin/websockets/pull/788 needs to be merged.

## ntabconsole.py ##
`Usage: python3 ntabconsole.py -h host [-u username] [-p password]`

Copyes from standard input to the NTablet's serial console; copies
from the NTablet's serial console to stdout.
Enter `~.` at the start of a line to break out of the connection;
enter `~r` to geenrate a reset signal.

## ntabreset.py ##
`Usage: python3 ntabreset.py -h host [-u username] [-p password]`

Generates a reset signal to the NTablet.

