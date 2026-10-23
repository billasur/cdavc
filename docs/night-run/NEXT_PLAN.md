CD-AVC next improvements (20 Oct 2026). Evidence: gpt-oss-20b via Groq, t=0.7, seed 1, dev2 (13 tasks), NOT comparable to REPORT30. One seed, small N. Token costs are ESTIMATES (measured ~1.7K tokens/attempt, ~22K for a 13-task single arm).

Measured so far: single 4/13, retry 8/13, cdavc 8/13. Format failures: 4/13 single answers were unparseable; 6 raw failures captured, 5 recoverable by the lenient parser, 1 of those was a correct solution. Other failures after 3 attempts (e02, e04, e05, e13) are code logic.

1. PICK: make the lenient parser the default and save every raw response (PARSING, not model quality). Evidence: missing "}" and "]" closers, one correct e04 solution thrown away. Cost 0 to switch; first paid run measures it. Confirmed if format failures fall from 4/13 to <=1/13 single with no new wrong passes (hidden tests still gate). Refuted if it recovers nothing new.
2. Gating: send cdavc the SyntaxError line/column instead of "AST contract failed". Evidence: cdavc e04 failed the AST gate 3 times with no detail; baseline retry got the line number. Cost about 12K (e04, e10, e11, e13). Confirmed if cdavc passes tasks it now loses to syntax errors. This is the only hypothesis where cdavc's design costs it points.
3. Settle the arm ordering with 2 more seeds on dev2 (STATISTICS). Evidence: old dev ordering flipped between seeds (6/8, 8/8, 7/8), and retry == cdavc here. Cost about 130K for 2 seeds x 3 arms; do after item 1 so parsing noise is gone. Confirmed if the paired CI on cdavc minus retry excludes 0. Otherwise report a tie.
4. Prompt (PROMPT): add one line telling the model to end with a complete JSON object. Skip if item 1 ships; the parser fixes it for free.
5. Model quality: no pipeline fix expected for e02/e04/e05/e13 logic failures. Optional check, about 25K: run gpt-oss-120b on dev2. If it sits at the ceiling, dev2 only separates arms for the 20B.

SKIP: H-a response_format (0/8 on allam, no gain), H-b prompt layout (no gain), patch-D, ast-raise-class, hidden-guidance-escalation, exp-1/2 (no dev failures they could fix), more qwen/allam slices (qwen at ceiling, allam near 0).
Classes: parser = item 1; gating = item 2; prompt = item 4; model quality = item 5 and the logic failures.
