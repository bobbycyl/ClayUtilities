import argparse
import random

from clayutil.futil import Properties


class Lottery(object):
    def __init__(self, filename, times):
        self.p = Properties(filename)
        self.pd = self.p.properties
        try:
            self.max = self.pd.pop("max")
        except KeyError:
            self.max = 0
        self.times = times
        self.pd["paid"] = self.pd.get("paid", 0)
        self.paid = self.pd.pop("paid")
        self.main()

    def main(self):
        print(self.pd)
        cumulative_probability = 0.0
        awards_distribution = {}
        for award, probability in self.pd.items():
            cumulative_probability += float(probability)
            awards_distribution[award] = cumulative_probability
        if cumulative_probability != 1:
            raise ValueError(
                "cumulative probability is %f, but 1.0 required"
                % cumulative_probability
            )
        for i in range(args.times):
            self.paid += 1
            if self.paid == self.max:
                r = 0.0
                self.paid = 0
            else:
                r = random.random()
            for award, award_cumulative_probability in awards_distribution.items():
                if r < award_cumulative_probability:
                    print(r, award)
                    break
        self.pd["max"] = self.max
        self.pd["paid"] = self.paid
        self.p.override()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--times", type=int, default=1)
    args = parser.parse_args()
    l0 = Lottery(args.filename, args.times)
