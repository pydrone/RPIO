"""
Command-line interface to RPIO. This script takes uses new functions
in py_gpio.c, namely `forceinput()` and `forceoutput()`. To use those
you'll need at least RPIO v0.1.8 (`sudo pip install --upgrade RPIO`).

Commands which will not change a gpio setup (eg. from OUTPUT to INPUT):

    Show the function and state of gpios (with -s/--show):

        $ RPIO_cmd.py --show 17
        $ RPIO_cmd.py --show 17,18,19
        $ RPIO_cmd.py --show 2-24

        # Example output for `$ PIO_cmd.py -r 4-10`
        GPIO 4 : INPUT   [0]
        GPIO 5 : ALT0    [0]
        GPIO 6 : OUTPUT  [1]
        GPIO 7 : INPUT   [0]
        GPIO 8 : INPUT   [0]
        GPIO 9 : INPUT   [0]
        GPIO 10: INPUT   [1]

    Set a GPIO to either `0` or `1` (with -w/--write):

        $ RPIO_cmd.py --write 17:1

        You can only write to pins that have been set up as OUTPUT; else you
        will need to set it yourself (eg. `--setoutput 17`).

    Show interrupt events on GPIOs (with -i/--interrupt; default edge='both'):

        $ RPIO_cmd.py --interrupt 17
        $ RPIO_cmd.py --interrupt 17:rising,18:falling,19
        $ RPIO_cmd.py --interrupt 17-24:rising

Commands which will change a pin setup (eg. from OUT to IN):

    Setup a pin as INPUT (optionally with pullup or -down resistor):

        RPIO_cmd.py --setinput 17
        RPIO_cmd.py --setinput 17:pullup
        RPIO_cmd.py --setinput 17:pulldown

    Setup a pin as OUTPUT:

        RPIO_cmd.py --setoutput 18

Author: Chris Hager <chris@linuxuser.at>
URL: https://github.com/metachris/raspberrypi-utils
"""
from optparse import OptionParser
import logging
from logging import debug, info, warn, error

RPIO_VERSION_MIN = "0.1.8"
GPIO_FUNCTIONS = {0: "OUTPUT", 1: "INPUT", 4: "ALT0", 7: "-"}


def error_gpio_outdated():
        print(("Please update RPIO to a newer version (eg. "
                "`sudo pip install --upgrade RPIO`)."))
        exit(1)


def interrupt_callback(gpio_id, value):
    logging.info("GPIO %s interrupt: value=%s" % (gpio_id, value))


# Optional: Command line interface
if __name__ == "__main__":
    # Prepare help and options
    usage = """usage: %prog options"""
    desc = """RPIO command line interface"""
    parser = OptionParser(usage=usage, description=desc)
    parser.add_option("-s", "--show", dest="show",
            help=("Show GPIO function (IN/OUT/ALT0) and state. For multiple "
                "GPIO's, separate the ids with a comma (eg. `-r 17,18,19`) "
                "or specify a range (eg. `-r 2-20`)"), metavar="gpio-id")

    parser.add_option("-i", "--interrupt", dest="interrupt",
            help=("Show interrupt events on specified gpio-id:edge (eg. "
                "`17:both`). For multiple GPIO's, separate the ids with a "
                "comma (eg. -i 17:both,18:falling) or specify a range (eg. "
                "`-r 2-20`)"), metavar="gpio-id")

    parser.add_option("-w", "--write", dest="write",
            help=("Set a GPIO output to either 1 or 0. Eg. `--write 17:0`"),
            metavar="gpio-id")

    parser.add_option("--setoutput", dest="setoutput",
            help="Setup GPIO as OUTPUT.", metavar="gpio-id")

    parser.add_option("--setinput", dest="setinput",
            help=("Setup GPIO as OUTPUT. To specify a pullup or -down resistor"
                ", add `pullup` or `pulldown` after the gpio-id (eg. "
                "`--setinput 17:pulldown`)"), metavar="gpio-id")

    parser.add_option("-v", "--verbose", dest="verbose", action="store_true")

    # Parse options and arguments now
    (options, args) = parser.parse_args()

    # We need to set the loglevel before importing RPIO
    if options.verbose:
        log_level = logging.DEBUG
        log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
    else:
        log_level = logging.INFO
        log_format = '%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    import RPIO
    if RPIO.VERSION < RPIO_VERSION_MIN:
        error_gpio_outdated()

    # Process startup argument
    if options.show:
        # gpio-ids can either be a single value, comma separated or a range
        if "-" in options.show:
            # eg 2-20
            n1, n2 = options.show.split("-")
            gpio_ids = [n for n in xrange(int(n1), int(n2) + 1)]
        else:
            gpio_ids = options.show.split(",")

        for gpio_id_str in gpio_ids:
            gpio_id = int(gpio_id_str)
            f = RPIO.gpio_function(gpio_id)
            info("GPIO %-2s: %-7s [%s]" % (gpio_id, GPIO_FUNCTIONS[f], 1 if \
                    RPIO.forceinput(gpio_id) else 0))

    elif options.write:
        gpio_id_str, value_str = options.write.split(":")
        gpio_id = int(gpio_id_str)
        f = RPIO.gpio_function(gpio_id)
        if f == 0:
            RPIO.forceoutput(gpio_id, int(value_str))

        else:
            error(("Cannot output to GPIO %s, because it is setup as %s. Use "
                    "--setoutput %s first.") % (gpio_id_str, \
                    GPIO_FUNCTIONS[f], gpio_id))

    elif options.interrupt:
        # gpio-ids can either be a single value, comma separated or a range
        if "-" in options.interrupt:
            # eg 2-20
            n1, n2 = options.interrupt.split("-")
            gpio_ids = [n for n in xrange(int(n1), int(n2) + 1)]
        else:
            gpio_ids = options.interrupt.split(",")

        for gpio_id_str in gpio_ids:
            parts = gpio_id_str.split(":")
            gpio_id = int(parts[0])
            edge = "both" if len(parts) == 1 else parts[1]
            RPIO.add_interrupt_callback(gpio_id, interrupt_callback, edge=edge)
            info("GPIO %s interrupt setup complete (edge detection='%s')" % \
                    (gpio_id, edge))
        info("Waiting for interrupts (exit with Ctrl+C) ...")
        try:
            RPIO.wait_for_interrupts()

        except KeyboardInterrupt:
            RPIO.cleanup()

    elif options.setoutput:
        gpio_id = int(options.setoutput)
        RPIO.setup(gpio_id, RPIO.OUT)

    elif options.setinput:
        parts = options.setinput.split(":")
        gpio_id = int(parts[0])
        if len(parts) == 1:
            RPIO.setup(gpio_id, RPIO.IN)
            debug("GPIO %s setup as INPUT" % gpio_id)
        else:
            if parts[1] == "pullup":
                RPIO.setup(gpio_id, RPIO.IN, pull_up_down=RPIO.PUD_UP)
                debug("GPIO %s setup as INPUT with PULLUP resistor" % gpio_id)
            elif parts[1] == "pulldown":
                RPIO.setup(gpio_id, RPIO.IN, pull_up_down=RPIO.PUD_DOWN)
                debug("GPIO %s setup as INPUT with PULLDOWN resistor" % \
                        gpio_id)
            else:
                raise ValueError("Error: %s is not `pullup` or `pulldown`" % \
                        gpio_id)

    else:
        parser.print_help()
