#!/usr/bin/python

from gatusgenerator import GatusGenerator

def main():
    updater = GatusGenerator()

    # This blocks
    updater.enter_update_loop()


if __name__ == "__main__":
    main()
