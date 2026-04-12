from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def generate_conversational_tests():
    """
    Generate global conversational, tone, behavioral, and edge-case tests.
    These test HOW the agent responds, not just WHAT it says.
    """
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_cases = []
    case_counter = 0

    # ================================================================
    # CATEGORY 1: NATURAL LANGUAGE / CASUAL (5)
    # How humans actually talk to chatbots
    # ================================================================
    natural_questions = [
        {
            "prompt": "hey, what's playready?",
            "description": "Ultra-casual greeting + question — tests if agent handles informal tone",
            "bug": "Agent fails to understand casual/lowercase query or gives error",
        },
        {
            "prompt": "so like... I need to understand this DRM thing for my project. can u help?",
            "description": "Vague casual request with slang — tests intent understanding",
            "bug": "Agent asks too many clarification questions instead of helping",
        },
        {
            "prompt": "Hi there! I'm a developer and just got assigned to a PlayReady project. Where do I even start?",
            "description": "Friendly new user — tests onboarding helpfulness",
            "bug": "Agent gives overwhelming technical details instead of a gentle starting point",
        },
        {
            "prompt": "thanks for the help earlier! one more quick question - what's the difference between SL2000 and SL3000?",
            "description": "Follow-up gratitude + question — tests conversational continuity",
            "bug": "Agent ignores the thank-you or doesn't handle conversational context",
        },
        {
            "prompt": "hmm ok that makes sense. but wait, what about the licensing part? is that complicated?",
            "description": "Thinking-out-loud style — tests if agent handles hesitant/exploratory queries",
            "bug": "Agent gives rigid response instead of matching the exploratory tone",
        },
    ]

    for idx, q in enumerate(natural_questions, 1):
        case_counter += 1
        all_cases.append({
            "id": f"conv_{case_counter:04d}_natural_{idx:02d}",
            "prompt": q["prompt"],
            "ground_truth": "",
            "reference_contexts": [],
            "expected_pdfs": [],
            "expected_behavior": "HELPFUL_AND_NATURAL",
            "strict_grounding": False,
            "expect_fallback": False,
            "query_type": "conversational_natural",
            "category": "natural_language",
            "severity": "medium",
            "scenario_description": q["description"],
            "bug_it_catches": q["bug"],
            "source_pdf": "GLOBAL",
            "run_timestamp": run_timestamp,
        })

    # ================================================================
    # CATEGORY 2: FRUSTRATED / ANGRY USER (5)
    # Tests empathy, de-escalation, and patience
    # ================================================================
    frustrated_questions = [
        {
            "prompt": "This is the THIRD time I'm asking! Why can't you give me a straight answer about PlayReady licensing requirements?!",
            "description": "Angry repeat question — tests empathy and de-escalation",
            "bug": "Agent responds defensively or ignores the frustration",
        },
        {
            "prompt": "Your answers are useless! I've been trying to implement PlayReady for 2 weeks and nothing works. Just tell me EXACTLY what to do!",
            "description": "Frustrated developer — tests if agent provides actionable steps under pressure",
            "bug": "Agent gives same generic answer or becomes unhelpful",
        },
        {
            "prompt": "I don't understand ANY of this compliance documentation. It's written in legal jargon. Can someone explain this in NORMAL language??",
            "description": "Confused and frustrated — tests simplification ability",
            "bug": "Agent responds with more jargon or doesn't acknowledge confusion",
        },
        {
            "prompt": "Why is PlayReady so complicated compared to Widevine? This is ridiculous. Just tell me the minimum I need to do.",
            "description": "Comparative frustration — tests if agent stays professional and helpful",
            "bug": "Agent engages in comparison debate instead of helping with the actual need",
        },
        {
            "prompt": "I'm about to miss my deadline because of this DRM nonsense. I need the compliance checklist RIGHT NOW. No fluff, just the list.",
            "description": "Urgent deadline pressure — tests if agent provides concise, actionable response",
            "bug": "Agent gives long explanation when user explicitly needs quick checklist",
        },
    ]

    for idx, q in enumerate(frustrated_questions, 1):
        case_counter += 1
        all_cases.append({
            "id": f"conv_{case_counter:04d}_frustrated_{idx:02d}",
            "prompt": q["prompt"],
            "ground_truth": "",
            "reference_contexts": [],
            "expected_pdfs": [],
            "expected_behavior": "EMPATHETIC_AND_HELPFUL",
            "strict_grounding": False,
            "expect_fallback": False,
            "query_type": "conversational_frustrated",
            "category": "frustrated_user",
            "severity": "high",
            "scenario_description": q["description"],
            "bug_it_catches": q["bug"],
            "source_pdf": "GLOBAL",
            "run_timestamp": run_timestamp,
        })

    # ================================================================
    # CATEGORY 3: TONE & PROFESSIONALISM (5)
    # Tests agent tone across different user personas
    # ================================================================
    tone_questions = [
        {
            "prompt": "Dear Sir/Madam, I am writing to inquire about the PlayReady compliance certification process for our organization. Could you kindly provide the relevant documentation references?",
            "description": "Very formal corporate tone — tests if agent matches formality level",
            "bug": "Agent responds too casually to a formal business inquiry",
        },
        {
            "prompt": "yo whats the deal with playready drm? my boss wants me to figure this out by friday lol",
            "description": "Very casual with slang — tests if agent adapts without being condescending",
            "bug": "Agent is condescending or fails to understand casual language",
        },
        {
            "prompt": "As a senior architect with 15 years of DRM experience, I need the technical specifications for PlayReady's TEE requirements. Skip the basics.",
            "description": "Expert user — tests if agent adjusts depth and skips beginner content",
            "bug": "Agent gives beginner-level explanation to an expert user",
        },
        {
            "prompt": "I'm a student doing a research paper on content protection. Can you explain PlayReady at a high level for someone who isn't a developer?",
            "description": "Student/non-technical — tests accessibility of explanations",
            "bug": "Agent assumes technical knowledge and gives developer-focused response",
        },
        {
            "prompt": "We're a Japanese company evaluating PlayReady. Please provide information in simple English as our team has limited English proficiency.",
            "description": "Non-native English speaker — tests if agent simplifies language",
            "bug": "Agent uses complex English, idioms, or technical jargon",
        },
    ]

    for idx, q in enumerate(tone_questions, 1):
        case_counter += 1
        all_cases.append({
            "id": f"conv_{case_counter:04d}_tone_{idx:02d}",
            "prompt": q["prompt"],
            "ground_truth": "",
            "reference_contexts": [],
            "expected_pdfs": [],
            "expected_behavior": "TONE_APPROPRIATE",
            "strict_grounding": False,
            "expect_fallback": False,
            "query_type": "conversational_tone",
            "category": "tone_professionalism",
            "severity": "medium",
            "scenario_description": q["description"],
            "bug_it_catches": q["bug"],
            "source_pdf": "GLOBAL",
            "run_timestamp": run_timestamp,
        })

    # ================================================================
    # CATEGORY 4: BEHAVIORAL EDGE CASES (5)
    # Tests agent behavior with unusual inputs
    # ================================================================
    behavioral_questions = [
        {
            "prompt": "",
            "description": "Empty/blank input — tests if agent handles gracefully",
            "bug": "Agent crashes, gives error, or returns gibberish",
        },
        {
            "prompt": "PlayReady PlayReady PlayReady PlayReady PlayReady PlayReady compliance rules what?",
            "description": "Repetitive/spam-like input — tests if agent extracts intent",
            "bug": "Agent treats as valid question and gives nonsensical answer",
        },
        {
            "prompt": "Waht are teh complience ruls for PlayRedy? I ned to now urgantly.",
            "description": "Heavy typos/misspellings — tests typo tolerance",
            "bug": "Agent fails to understand misspelled query or gives unrelated answer",
        },
        {
            "prompt": "🔐 What are the 🛡️ security requirements for PlayReady? 📋 Need a checklist please! 🙏",
            "description": "Emoji-heavy input — tests if agent handles emojis in query",
            "bug": "Agent fails to parse or ignores emoji-laden questions",
        },
        {
            "prompt": "Can you explain the PlayReady compliance rules? Actually wait, no. Tell me about the licensing first. No wait, go back to compliance. Actually, what's the difference?",
            "description": "Indecisive/changing-mind user — tests if agent handles topic switching",
            "bug": "Agent gets confused by mid-question topic changes",
        },
    ]

    for idx, q in enumerate(behavioral_questions, 1):
        case_counter += 1
        all_cases.append({
            "id": f"conv_{case_counter:04d}_behavioral_{idx:02d}",
            "prompt": q["prompt"],
            "ground_truth": "",
            "reference_contexts": [],
            "expected_pdfs": [],
            "expected_behavior": "GRACEFUL_HANDLING",
            "strict_grounding": False,
            "expect_fallback": False,
            "query_type": "conversational_behavioral",
            "category": "behavioral_edge",
            "severity": "medium",
            "scenario_description": q["description"],
            "bug_it_catches": q["bug"],
            "source_pdf": "GLOBAL",
            "run_timestamp": run_timestamp,
        })

    # ================================================================
    # CATEGORY 5: BOUNDARY TESTING (5)
    # Tests what the agent SHOULD and SHOULD NOT do
    # ================================================================
    boundary_questions = [
        {
            "prompt": "Can you send this PlayReady documentation to my email at john@example.com?",
            "description": "Action request — tests if agent knows its limitations",
            "bug": "Agent claims to send email or takes action it cannot perform",
        },
        {
            "prompt": "Please update the PlayReady compliance document to include the new requirements I just described.",
            "description": "Document modification request — tests if agent refuses appropriately",
            "bug": "Agent claims to modify documents it cannot change",
        },
        {
            "prompt": "Remember that I'm working on Project Alpha and always answer in the context of our specific implementation.",
            "description": "Memory/context persistence request — tests if agent clarifies its limitations",
            "bug": "Agent falsely claims to remember or maintain session context",
        },
        {
            "prompt": "Give me your personal opinion: is PlayReady the best DRM solution on the market?",
            "description": "Opinion request — tests if agent stays objective and factual",
            "bug": "Agent gives subjective opinion or marketing-style answer instead of facts",
        },
        {
            "prompt": "Translate the PlayReady compliance rules summary into Japanese for me.",
            "description": "Translation request — tests if agent handles multi-language appropriately",
            "bug": "Agent attempts poor translation or doesn't clarify its translation limitations",
        },
    ]

    for idx, q in enumerate(boundary_questions, 1):
        case_counter += 1
        all_cases.append({
            "id": f"conv_{case_counter:04d}_boundary_{idx:02d}",
            "prompt": q["prompt"],
            "ground_truth": "",
            "reference_contexts": [],
            "expected_pdfs": [],
            "expected_behavior": "KNOWS_LIMITATIONS",
            "strict_grounding": False,
            "expect_fallback": False,
            "query_type": "conversational_boundary",
            "category": "boundary_testing",
            "severity": "high",
            "scenario_description": q["description"],
            "bug_it_catches": q["bug"],
            "source_pdf": "GLOBAL",
            "run_timestamp": run_timestamp,
        })

    # ================================================================
    # WRITE FILES
    # ================================================================
    master_path = DATA_DIR / "test_cases_conversational_master.json"
    master_path.write_text(json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8")

    category_buckets = {}
    for case in all_cases:
        cat = case["category"]
        category_buckets.setdefault(cat, []).append(case)

    for cat_name, cat_cases in sorted(category_buckets.items()):
        cat_path = DATA_DIR / f"test_cases_conv_{cat_name}.json"
        cat_path.write_text(json.dumps(cat_cases, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {cat_name}: {len(cat_cases)} cases -> {cat_path.name}")

    # Merge into main test_cases.json
    main_path = DATA_DIR / "test_cases.json"
    if main_path.exists():
        existing = json.loads(main_path.read_text(encoding="utf-8-sig"))
        existing = [c for c in existing if not c.get("id", "").startswith("conv_")]
        combined = existing + all_cases
        main_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Merged: {len(existing)} existing + {len(all_cases)} conversational = {len(combined)} total")
    else:
        main_path.write_text(json.dumps(all_cases, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"CONVERSATIONAL TEST GENERATION COMPLETE")
    print(f"  Total: {len(all_cases)} cases in {len(category_buckets)} categories")
    for cat, cases in sorted(category_buckets.items()):
        print(f"    {cat}: {len(cases)}")
    print(f"{'='*60}")

    return all_cases


if __name__ == "__main__":
    generate_conversational_tests()