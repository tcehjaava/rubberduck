import csv
import json
import logging

from rubberduck.agents.autonomous import AutonomousAgent
from rubberduck.models.autonomous_config import AutonomousAgentConfig
from rubberduck.utils.dataset_utils import DatasetUtils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_prompt(instance):
    return f"""Analyze this software engineering problem and provide a JSON response.

CONTEXT:
- You are reviewing a real-world code change from an open-source project
- The "Problem Statement" describes what needs to be fixed/implemented
- The "Patch" shows the actual code changes that solve the problem
- The "Test Patch" contains tests that verify the solution works correctly

Problem Statement:
{instance.problem_statement}

Patch (Actual Solution):
{instance.patch}

Test Patch (Tests that should pass after applying the patch):
{instance.test_patch if instance.test_patch else "No test patch provided"}

EVALUATION CRITERIA:

1. COMPLEXITY_PERCENTAGE (0-100):
   - 0-25: Simple changes (typos, constant changes, simple logic fixes)
   - 25-50: Moderate changes (small feature additions, bug fixes requiring domain knowledge)
   - 50-75: Complex changes (multiple file modifications, algorithm implementations, architectural adjustments)
   - 75-100: Very complex (major refactoring, complex algorithms, deep framework modifications)

   Consider:
   - Number of files changed
   - Lines of code modified
   - Algorithmic complexity
   - Required domain expertise
   - Interconnected system changes

2. CATEGORY:
   - "easy": Can be solved by pattern matching or simple logic
   - "medium": Requires understanding of the codebase and programming concepts
   - "hard": Needs deep understanding of the system architecture and complex problem solving
   - "very hard": Requires expert-level knowledge and creative solutions

3. SOLVABILITY_PERCENTAGE (0-100):
   - 0-25: Nearly impossible (vague requirements, missing context, requires human creativity)
   - 25-50: Difficult (ambiguous specs, multiple valid solutions, limited test coverage)
   - 50-75: Achievable (clear requirements, good test coverage, well-defined scope)
   - 75-100: Highly solvable (precise specs, comprehensive tests, isolated changes)

   Consider:
   - Clarity of problem statement
   - Completeness of test coverage
   - Availability of context clues
   - Uniqueness of correct solution

4. REASONING:
   Explain your assessment covering:
   - What makes this problem complex/simple
   - Key challenges in generating the correct patch
   - Why the solvability percentage is high/low
   - Any specific domain knowledge required

Provide JSON response:
{{
    "complexity_percentage": <0-100>,
    "category": <"easy", "medium", "hard", "very hard">,
    "solvability_percentage": <0-100>,
    "reasoning": "<detailed explanation>"
}}

Respond with ONLY the JSON object."""


def parse_response(text):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        logger.info(f"Failed to parse response: {text}")
        return {
            "complexity_percentage": -1,
            "category": "error",
            "solvability_percentage": -1,
            "reasoning": "Failed to parse response",
        }


def analyze_instances():
    config = AutonomousAgentConfig(
        model_config="o3-2025-04-16",
        assistant_name="Analyzer",
        proxy_name="User",
        system_message="""You are an expert software engineer with deep experience in code analysis and automated
program repair.

Your expertise includes:
- Analyzing code complexity across various programming languages and frameworks
- Understanding software testing and test coverage
- Evaluating the feasibility of automated code generation
- Assessing problem specifications for clarity and completeness

Your task is to evaluate software engineering problems by examining:
1. The problem description (what needs to be fixed/implemented)
2. The actual solution (the patch that fixes it)
3. The tests that verify the solution

You must provide objective, quantitative assessments based on clear criteria. Your analysis should consider both the
technical complexity of the code changes and the likelihood that an AI system could generate the correct solution
given only the problem statement.

Always respond with valid JSON in the exact format requested. Be precise in your percentages and thorough in your
reasoning.""",
        max_turns=1,
    )

    agent = AutonomousAgent(config)
    results = []

    dataset = DatasetUtils._load_split("test", False)
    instance_ids = [row["instance_id"] for row in dataset]

    for idx, instance_id in enumerate(instance_ids):
        logger.info(f"Processing {idx + 1}/{len(instance_ids)}: {instance_id}")

        try:
            instance = DatasetUtils.load_instance(instance_id=instance_id)
            chat_result = agent.execute_task(create_prompt(instance))
            response = chat_result.chat_history[-1]["content"]

            analysis = parse_response(response)
            analysis["instance_id"] = instance_id
            results.append(analysis)

        except Exception as e:
            logger.error(f"Error: {instance_id}: {e}")
            results.append(
                {
                    "instance_id": instance_id,
                    "complexity_percentage": -1,
                    "category": "error",
                    "solvability_percentage": -1,
                    "reasoning": str(e),
                }
            )

    with open("instance_analysis.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["instance_id", "complexity_percentage", "category", "solvability_percentage", "reasoning"]
        )
        writer.writeheader()
        writer.writerows(results)

    return results


if __name__ == "__main__":
    results = analyze_instances()

    valid = [r for r in results if r["complexity_percentage"] >= 0]
    if valid:
        print(f"\nAnalyzed: {len(results)}")
        print(f"Successful: {len(valid)}")
        print(f"Avg complexity: {sum(r['complexity_percentage'] for r in valid) / len(valid):.1f}%")
        print(f"Avg solvability: {sum(r['solvability_percentage'] for r in valid) / len(valid):.1f}%")
