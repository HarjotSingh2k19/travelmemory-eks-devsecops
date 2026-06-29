import json
import os
import sys
import requests

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: could not load {path}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 4:
        print("Usage: scan-triage.py <trivy.json> <checkov.json> <gitleaks.json>")
        sys.exit(1)

    trivy_path, checkov_path, gitleaks_path = sys.argv[1], sys.argv[2], sys.argv[3]

    trivy = load_json(trivy_path)
    checkov = load_json(checkov_path)
    gitleaks = load_json(gitleaks_path)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FAIL CLOSED: GEMINI_API_KEY not set — cannot triage, blocking pipeline.")
        sys.exit(1)

    prompt = f"""You are a security triage assistant for a CI/CD pipeline.
Given these raw scan results, respond with STRICT JSON only, no markdown, no preamble:
{{"verdict": "PASS" or "BLOCK", "summary": "2-3 sentence plain-English summary", "top_findings": ["at most 5 findings ranked by real exploitability"]}}

Trivy (container image CVEs): {json.dumps(trivy)[:6000]}

Checkov (Terraform IaC misconfigurations): {json.dumps(checkov)[:6000]}

gitleaks (hardcoded secrets): {json.dumps(gitleaks)[:4000]}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
    except Exception as e:
        print(f"FAIL CLOSED: triage call failed or returned unparseable output: {e}")
        sys.exit(1)

    print(f"VERDICT: {result.get('verdict')}")
    print(f"SUMMARY: {result.get('summary')}")
    for finding in result.get("top_findings", []):
        print(f"  - {finding}")

    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if slack_webhook:
        try:
            requests.post(slack_webhook, json={
                "text": f":robot_face: *CI Security Triage* — {result.get('verdict')}\n{result.get('summary')}\n" +
                        "\n".join(f"• {f}" for f in result.get("top_findings", []))
            }, timeout=10)
        except Exception as e:
            print(f"WARNING: Slack notification failed (non-blocking): {e}")

    sys.exit(0 if result.get("verdict") == "PASS" else 1)

if __name__ == "__main__":
    main()