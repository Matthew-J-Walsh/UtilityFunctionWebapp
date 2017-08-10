import argparse

def main(arguments):
    if isinstance(arguments, dict):
        result = add(arguments[arguments.keys()[0]],arguments[arguments.keys()[1]])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("-a", help="Number One.", type=float, default=5)
        parser.add_argument("-b", help="Number Two.", type=float, default=2)
        args = parser.parse_args(args=arguments)
        result = add(args.a, args.b)
    return result

def add(a , b):
    return int(a) + int(b)

if __name__ == '__main__':
    import sys
    print(main(sys.argv[1:]))