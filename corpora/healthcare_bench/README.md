# QFIRE-HealthBench: a healthcare prompt-injection benchmark

**1000 benign + 1000 malicious** healthcare prompts for evaluating LLM
prompt firewalls in clinical settings.

## Malicious provenance (by source)
- native (healthcare threats authored here): 400
- garak (real NVIDIA/garak DAN-family + in-the-wild jailbreaks, healthcare-wrapped): 300
- pyrit (real Microsoft PyRIT converters): 300

Categories: {'bulk_export': 39, 'phi_exfil': 127, 'cross_patient': 86, 'jailbreak': 415, 'phi_smuggle': 26, 'clinical_advice': 185, 'reidentification': 39, 'system_exfil': 29, 'direct_injection': 54}
Obfuscation techniques: {'none': 700, 'morse': 33, 'rot13': 34, 'base64': 34, 'ascii_smuggler': 33, 'leetspeak': 33, 'binary': 33, 'caesar': 33, 'unicode_confusable': 33, 'atbash': 34}

## Benign
Realistic clinical-adjacent requests (general health info, scheduling, med/insurance
admin, lab-result *general* explanation, wellness, mental-health resources,
records-access-for-self) that a healthcare assistant SHOULD allow. Over-blocking
these is a failure mode.

## Malicious
PHI exfiltration, re-identification, cross-patient access, bulk export, out-of-scope
clinical advice (diagnosis/dosing), system-prompt exfiltration, direct injection,
and real DAN/jailbreak framings — plus obfuscated variants produced by real PyRIT
converters (Base64/ROT13/Atbash/Leetspeak/Unicode/Binary/...).

## Ethics & licensing
Defensive benchmark. **All identifiers are synthetic**; no real PHI. Malicious =
scope-violation / injection / PHI-solicitation, not operational-harm content.
Seeds: garak (Apache-2.0, NVIDIA); converters: Microsoft PyRIT (MIT). Generated
deterministically (seed 1337) by scripts/gen_healthcare_dataset.py + scripts/pyrit_convert.py.
