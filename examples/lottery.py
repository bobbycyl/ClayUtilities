import argparse
import random

from clayutil.futil import Properties


class Lottery(object):
    def __init__(self, filename, times):
        self.p = Properties(filename)
        self.p.load()
        try:
            self.max = self.p.pop("max")
        except KeyError:
            self.max = 0
        self.times = times
        self.p["paid"] = self.p.get("paid", 0)
        self.paid = self.p.pop("paid")
        self.main()

    def main(self):
        print(self.p)
        cumulative_probability = 0.0
        prizes_distribution = {}
        for prize, probability in self.p.items():
            if prize[0] == "#":
                continue
            try:
                cumulative_probability += float(probability)
            except ValueError:
                raise ValueError("probability %r must be a number" % probability) from None
            prizes_distribution[prize] = cumulative_probability
        if cumulative_probability != 1:
            raise ValueError("cumulative probability is %f, but 1.0 required" % cumulative_probability)
        print(prizes_distribution)
        for i in range(args.times):
            self.paid += 1
            if self.paid == self.max:
                r = 0.0
                print("@", end="")
                self.paid = 0
            else:
                r = random.random()
            for prize, prize_cumulative_probability in prizes_distribution.items():
                if r < prize_cumulative_probability:
                    print(r, prize)
                    break
        self.p["max"] = self.max
        self.p["paid"] = self.paid
        self.p.dump()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--times", type=int, default=1)
    args = parser.parse_args()
    l0 = Lottery(args.filename, args.times)
