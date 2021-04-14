import sys

import ditto


CI_TEST = "--ci" in sys.argv


def main():
    if CI_TEST:
        ...

    sys.exit(0)


if __name__ == "__main__":
    main()
