import argparse

from clayutil.sutil import export_rsa_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    args = parser.parse_args()
    export_rsa_key(args.name)
