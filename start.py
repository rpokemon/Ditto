import asyncio
import sys

import ditto

CI_TEST = "--ci" in sys.argv


def main() -> None:
    bot = ditto.Bot()

    if CI_TEST:
        old_on_ready = bot.on_ready
        SLEEP_FOR = 5

        @bot.event
        async def on_ready():
            await old_on_ready()
            await asyncio.sleep(SLEEP_FOR)
            await bot.close()

    bot.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
