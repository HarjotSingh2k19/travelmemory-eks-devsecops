import json
import os
import sys
import requests
import time

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"FAIL CLOSED: could not load {path}: {e}")
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
    
    # --- ROBUST RETRY LOGIC ADDED HERE ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=body, timeout=30)
            
            # If Google's servers are overloaded, wait 15 seconds and try again
            if resp.status_code == 503:
                print(f"WARNING: 503 Service Unavailable from Gemini. Retrying {attempt+1}/{max_retries} in 15 seconds...")
                time.sleep(15)
                continue
                
            resp.raise_for_status() # Catch any other errors (like 403, 404, 429)
            
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(cleaned)
            break # Success! Break out of the retry loop
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"FAIL CLOSED: triage call failed after {max_retries} attempts: {e}")
                sys.exit(1)
            print(f"WARNING: Request failed ({e}). Retrying {attempt+1}/{max_retries} in 15 seconds...")
            time.sleep(15)
            
    # --------------------------------------

    print(f"VERDICT: {result.get('verdict')}")
    print(f"SUMMARY: {result.get('summary')}")
    for finding in result.get("top_findings", []):
        print(f"  - {finding}")
        
    sys.exit(0 if result.get("verdict") == "PASS" else 1)

if __name__ == "__main__":
    main()