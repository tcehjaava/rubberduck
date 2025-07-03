from utils.swebench_evaluator import SWEBenchEvaluator


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("instance_ids", nargs="+", help="Instance IDs")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    evaluator = SWEBenchEvaluator(max_workers=args.workers)
    evaluator.evaluate_instances(args.instance_ids)


if __name__ == "__main__":
    main()
