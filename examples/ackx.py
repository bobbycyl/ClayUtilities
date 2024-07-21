import argparse

from clayutil.futil import advanced_search

arg_parser = argparse.ArgumentParser("ack extended")
arg_parser.add_argument("directory")
arg_parser.add_argument("substring")
arg_parser.add_argument("--encoding-guess-length", type=int, default=256)
arg_parser.add_argument("--auto-clean", action="store_true")
arg_parser.add_argument("-o", "--output")
args = arg_parser.parse_args()
g = advanced_search(args.directory, args.substring, args.encoding_guess_length, args.auto_clean)
if args.output is None:
    last_filename = ""
    for filename, l, c, w in g:
        if filename != last_filename:
            print("\033[1m%s\033[0m" % filename)
            last_filename = filename
        print("\033[1;32m%d\033[0m:\033[1;32m%d\033[0m\t\033[31m%s\033[0m%s" % (l, c, args.substring, w))
else:
    with open(args.output, "w") as f:
        for filename, l, c, w in g:
            print(filename, l, c, w, file=f)
