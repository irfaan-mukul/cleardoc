"""
Customs Document Checker — Web Server
Run with: python app.py
Then open: http://localhost:5000
"""

import os
import json
import base64
import anthropic
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB max upload

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}

SYSTEM_PROMPT = """You are a senior customs compliance specialist with 20 years of experience 
in US import/export regulations. Your job is to review shipping documents and identify 
errors, omissions, and inconsistencies that could cause customs holds, delays, fines, 
or rejection at the border.

When reviewing a document, check for:

CRITICAL ISSUES (will likely cause customs hold or rejection):
- Missing required fields (shipper, consignee, country of origin, HTS codes, values)
- Invalid or malformed HTS codes (US import HTS codes must be 10 digits)
- Weight discrepancies between line items and declared totals
- Missing or inconsistent country of origin declarations
- Currency inconsistencies within the same document
- Valuation issues (undervaluation, missing freight/insurance for CIF terms)

WARNINGS (may cause delays or additional scrutiny):
- Address inconsistencies (ZIP code doesn't match city/state)
- Missing contact information
- Vague or insufficient goods descriptions
- Missing unit of measure
- Incoterms not clearly stated
- Missing purchase order or reference numbers

INFORMATIONAL (best practice notes):
- Fields that are present but could be more specific
- Documentation that is typically required alongside this document

Structure your response as a JSON object with this exact format:
{
  "document_type": "type of document reviewed",
  "overall_status": "HOLD" | "WARNING" | "CLEAR",
  "summary": "one sentence overall assessment",
  "issues": [
    {
      "severity": "CRITICAL" | "WARNING" | "INFO",
      "field": "name of the field or section with the issue",
      "issue": "clear description of what is wrong",
      "location": "where in the document this appears",
      "fix": "specific action needed to correct this"
    }
  ],
  "passed_checks": ["list of important fields that were correctly completed"],
  "recommendation": "overall recommendation — clear to ship, correct and resubmit, or hold"
}

Be thorough but precise. Only flag genuine issues, not stylistic preferences.
Respond with ONLY the JSON object — no text before or after it."""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def check_document(file_bytes, filename):
    ext = filename.rsplit(".", 1)[1].lower()
    media_type_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "application/pdf")
    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")

    client = anthropic.Anthropic()

    if media_type == "application/pdf":
        doc_block = {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": encoded}}
    else:
        doc_block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}}

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [doc_block, {"type": "text", "text": "Please review this shipping document for customs compliance issues."}]}]
    )

    raw = response.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            return {"error": "Could not parse response", "raw": raw}
    return {"error": "No JSON in response", "raw": raw}


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ClearDoc — Customs Compliance Checker</title>

<!-- Open Graph tags for LinkedIn/social previews -->
<meta property="og:title" content="ClearDoc — AI Customs Compliance Checker">
<meta property="og:description" content="Upload a shipping document and get an instant compliance report. Catches invalid HTS codes, weight discrepancies, currency mismatches, and missing fields.">
<meta property="og:image" content="https://raw.githubusercontent.com/irfaan-mukul/cleardoc/main/cleardoc_preview.png">
<meta property="og:url" content="https://cleardoc.onrender.com">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #0a1628;
    --navy-mid: #0f2040;
    --blue: #0f3460;
    --accent: #e8a838;
    --accent-light: #ffd97d;
    --green: #00c48c;
    --red: #ff4d6d;
    --yellow: #ffba08;
    --info: #4cc9f0;
    --surface: #111e35;
    --surface-2: #172440;
    --border: rgba(255,255,255,0.08);
    --text: #e8edf5;
    --text-muted: #7a8aaa;
    --font-display: 'DM Serif Display', Georgia, serif;
    --font-body: 'DM Sans', system-ui, sans-serif;
    --font-mono: 'DM Mono', monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--navy);
    color: var(--text);
    font-family: var(--font-body);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Background grid */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(15,52,96,0.3) 1px, transparent 1px),
      linear-gradient(90deg, rgba(15,52,96,0.3) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  .container {
    max-width: 860px;
    margin: 0 auto;
    padding: 40px 24px;
    position: relative;
    z-index: 1;
  }

  /* Header */
  header {
    text-align: center;
    margin-bottom: 48px;
    padding-top: 20px;
  }

  .logo-mark {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }

  .logo-icon {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, var(--accent), var(--accent-light));
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }

  .logo-text {
    font-family: var(--font-display);
    font-size: 28px;
    color: var(--text);
    letter-spacing: -0.5px;
  }

  .logo-text span { color: var(--accent); }

  header p {
    color: var(--text-muted);
    font-size: 15px;
    font-weight: 300;
    max-width: 460px;
    margin: 0 auto;
    line-height: 1.6;
  }

  /* Upload zone */
  .upload-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }

  .upload-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
  }

  .drop-zone {
    border: 1.5px dashed rgba(232,168,56,0.4);
    border-radius: 12px;
    padding: 48px 32px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
  }

  .drop-zone:hover, .drop-zone.dragover {
    border-color: var(--accent);
    background: rgba(232,168,56,0.05);
  }

  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }

  .drop-icon {
    font-size: 36px;
    margin-bottom: 12px;
    display: block;
  }

  .drop-title {
    font-size: 17px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 6px;
  }

  .drop-sub {
    font-size: 13px;
    color: var(--text-muted);
  }

  .file-selected {
    display: none;
    align-items: center;
    gap: 12px;
    background: rgba(0,196,140,0.1);
    border: 1px solid rgba(0,196,140,0.3);
    border-radius: 10px;
    padding: 14px 18px;
    margin-top: 16px;
  }

  .file-selected.visible { display: flex; }

  .file-selected .file-icon { font-size: 22px; }

  .file-selected .file-name {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--green);
    flex: 1;
  }

  .btn-check {
    width: 100%;
    margin-top: 20px;
    padding: 16px;
    background: linear-gradient(135deg, var(--accent), var(--accent-light));
    color: var(--navy);
    border: none;
    border-radius: 10px;
    font-family: var(--font-body);
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .btn-check:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(232,168,56,0.3); }
  .btn-check:active { transform: translateY(0); }
  .btn-check:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  /* Loading */
  .loading {
    display: none;
    text-align: center;
    padding: 48px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    margin-bottom: 32px;
  }

  .loading.visible { display: block; }

  .spinner {
    width: 44px;
    height: 44px;
    border: 3px solid rgba(232,168,56,0.2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 16px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .loading p {
    color: var(--text-muted);
    font-size: 14px;
  }

  .loading strong {
    display: block;
    color: var(--text);
    font-size: 16px;
    margin-bottom: 6px;
  }

  /* Results */
  #results { display: none; }
  #results.visible { display: block; }

  .status-banner {
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 18px;
  }

  .status-banner.HOLD {
    background: rgba(255,77,109,0.12);
    border: 1px solid rgba(255,77,109,0.3);
  }

  .status-banner.WARNING {
    background: rgba(255,186,8,0.1);
    border: 1px solid rgba(255,186,8,0.3);
  }

  .status-banner.CLEAR {
    background: rgba(0,196,140,0.1);
    border: 1px solid rgba(0,196,140,0.3);
  }

  .status-icon { font-size: 36px; flex-shrink: 0; }

  .status-text .status-label {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .HOLD .status-label { color: var(--red); }
  .WARNING .status-label { color: var(--yellow); }
  .CLEAR .status-label { color: var(--green); }

  .status-text .status-title {
    font-family: var(--font-display);
    font-size: 22px;
    color: var(--text);
    margin-bottom: 4px;
  }

  .status-text .status-summary {
    font-size: 14px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  /* Stats row */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
  }

  .stat-number {
    font-family: var(--font-display);
    font-size: 32px;
    margin-bottom: 2px;
  }

  .stat-label {
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .stat-card.critical .stat-number { color: var(--red); }
  .stat-card.warning .stat-number { color: var(--yellow); }
  .stat-card.passed .stat-number { color: var(--green); }

  /* Issues */
  .section-title {
    font-family: var(--font-display);
    font-size: 18px;
    color: var(--text);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .issue-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 10px;
    overflow: hidden;
    transition: border-color 0.2s;
  }

  .issue-card:hover { border-color: rgba(255,255,255,0.15); }

  .issue-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    cursor: pointer;
    user-select: none;
  }

  .severity-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .CRITICAL .severity-dot { background: var(--red); box-shadow: 0 0 8px var(--red); }
  .WARNING .severity-dot { background: var(--yellow); box-shadow: 0 0 8px var(--yellow); }
  .INFO .severity-dot { background: var(--info); box-shadow: 0 0 8px var(--info); }

  .severity-badge {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    padding: 3px 8px;
    border-radius: 4px;
    letter-spacing: 1px;
    flex-shrink: 0;
  }

  .CRITICAL .severity-badge { background: rgba(255,77,109,0.15); color: var(--red); }
  .WARNING .severity-badge { background: rgba(255,186,8,0.15); color: var(--yellow); }
  .INFO .severity-badge { background: rgba(76,201,240,0.15); color: var(--info); }

  .issue-field {
    font-size: 14px;
    font-weight: 600;
    flex: 1;
    color: var(--text);
  }

  .issue-toggle {
    color: var(--text-muted);
    font-size: 18px;
    transition: transform 0.2s;
  }

  .issue-card.open .issue-toggle { transform: rotate(180deg); }

  .issue-body {
    display: none;
    padding: 0 18px 16px;
    border-top: 1px solid var(--border);
  }

  .issue-card.open .issue-body { display: block; }

  .issue-row {
    display: grid;
    grid-template-columns: 80px 1fr;
    gap: 6px 12px;
    margin-top: 10px;
    font-size: 13px;
  }

  .issue-row-label {
    color: var(--text-muted);
    font-weight: 500;
    padding-top: 1px;
  }

  .issue-row-value { color: var(--text); line-height: 1.5; }

  .fix-value {
    color: var(--green);
    font-size: 13px;
    line-height: 1.5;
    background: rgba(0,196,140,0.05);
    border-left: 2px solid var(--green);
    padding: 6px 10px;
    border-radius: 0 6px 6px 0;
    margin-top: 2px;
  }

  /* Passed checks */
  .passed-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 24px;
  }

  .passed-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: var(--text-muted);
  }

  .passed-item::before {
    content: '✓';
    color: var(--green);
    font-weight: 700;
    flex-shrink: 0;
  }

  /* Recommendation */
  .recommendation-card {
    background: var(--surface-2);
    border: 1px solid rgba(232,168,56,0.2);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 32px;
  }

  .recommendation-card .rec-label {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .recommendation-card p {
    font-size: 14px;
    line-height: 1.7;
    color: var(--text);
  }

  .btn-reset {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 12px 24px;
    border-radius: 8px;
    font-family: var(--font-body);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    display: block;
    margin: 0 auto;
  }

  .btn-reset:hover { border-color: var(--text-muted); color: var(--text); }

  /* Instructions */
  .help-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--accent);
    padding: 10px 20px;
    border-radius: 8px;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    margin: 0 auto 24px;
    display: flex;
    letter-spacing: 0.3px;
  }

  .help-toggle:hover {
    border-color: var(--accent);
    background: rgba(232,168,56,0.06);
  }

  .help-toggle .arrow {
    transition: transform 0.2s;
    font-size: 11px;
  }

  .help-toggle.open .arrow { transform: rotate(180deg); }

  .help-panel {
    display: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }

  .help-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
  }

  .help-panel.visible { display: block; }

  .help-section {
    margin-bottom: 24px;
  }

  .help-section:last-child { margin-bottom: 0; }

  .help-section h3 {
    font-family: var(--font-display);
    font-size: 16px;
    color: var(--accent);
    margin-bottom: 10px;
  }

  .help-section p {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.7;
    margin-bottom: 8px;
  }

  .help-steps {
    list-style: none;
    padding: 0;
    counter-reset: steps;
  }

  .help-steps li {
    counter-increment: steps;
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
    font-size: 13px;
    color: var(--text);
    line-height: 1.6;
  }

  .help-steps li::before {
    content: counter(steps);
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    background: var(--blue);
    color: var(--accent);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    margin-top: 1px;
  }

  .help-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
  }

  .help-doc-type {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text);
  }

  .help-doc-type .doc-icon { font-size: 18px; flex-shrink: 0; }

  .severity-legend {
    display: flex;
    gap: 16px;
    margin-top: 10px;
    flex-wrap: wrap;
  }

  .severity-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .severity-item .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .severity-item .dot.crit { background: var(--red); }
  .severity-item .dot.warn { background: var(--yellow); }
  .severity-item .dot.info-dot { background: var(--info); }

  @media (max-width: 600px) {
    .help-grid { grid-template-columns: 1fr; }
    .severity-legend { flex-direction: column; gap: 8px; }
  }

  /* Footer */
  footer {
    text-align: center;
    padding: 32px 0 16px;
    color: var(--text-muted);
    font-size: 12px;
    position: relative;
    z-index: 1;
  }

  @media (max-width: 600px) {
    .stats-row { grid-template-columns: repeat(3, 1fr); }
    .passed-grid { grid-template-columns: 1fr; }
    .issue-row { grid-template-columns: 70px 1fr; }
  }
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="logo-mark">
      <div class="logo-icon">📋</div>
      <div class="logo-text">Clear<span>Doc</span></div>
    </div>
    <p>AI-powered customs compliance checking for commercial invoices, bills of lading, and packing lists.</p>
  </header>

  <!-- Help toggle -->
  <button class="help-toggle" id="helpToggle" onclick="toggleHelp()">
    <span>📖</span> How It Works <span class="arrow">▾</span>
  </button>

  <!-- Instructions panel -->
  <div class="help-panel" id="helpPanel">

    <div class="help-section">
      <h3>What ClearDoc Does</h3>
      <p>ClearDoc uses AI to review your shipping documents for customs compliance issues before you submit them. It catches errors that could cause holds, delays, fines, or rejection at the border — saving you time and money.</p>
    </div>

    <div class="help-section">
      <h3>How to Use It</h3>
      <ol class="help-steps">
        <li>Upload a shipping document by dragging it onto the upload area, or click to browse your files.</li>
        <li>Click <strong>Check Document</strong> and wait 15–30 seconds while the AI analyzes your file.</li>
        <li>Review the compliance report. Each issue is color-coded by severity — click any issue to expand it and see the recommended fix.</li>
        <li>Correct any critical or warning issues on your document and re-check if needed.</li>
      </ol>
    </div>

    <div class="help-section">
      <h3>Supported Documents</h3>
      <div class="help-grid">
        <div class="help-doc-type"><span class="doc-icon">🧾</span> Commercial Invoices</div>
        <div class="help-doc-type"><span class="doc-icon">🚢</span> Bills of Lading</div>
        <div class="help-doc-type"><span class="doc-icon">📦</span> Packing Lists</div>
        <div class="help-doc-type"><span class="doc-icon">📄</span> Customs Declarations</div>
      </div>
      <p style="margin-top:10px;">Accepted formats: PDF, PNG, JPG — up to 20MB per file.</p>
    </div>

    <div class="help-section">
      <h3>Understanding the Results</h3>
      <p>Issues are categorized into three severity levels:</p>
      <div class="severity-legend">
        <div class="severity-item"><div class="dot crit"></div> <strong>Critical</strong> — Will likely cause a customs hold or rejection. Must be fixed before submission.</div>
        <div class="severity-item"><div class="dot warn"></div> <strong>Warning</strong> — May cause delays or additional scrutiny. Should be reviewed.</div>
        <div class="severity-item"><div class="dot info-dot"></div> <strong>Info</strong> — Best practice suggestions to strengthen your documentation.</div>
      </div>
    </div>

    <div class="help-section">
      <h3>What ClearDoc Checks For</h3>
      <p>The AI reviews your document against common customs compliance requirements including: missing required fields, invalid or incomplete HTS codes, weight and quantity discrepancies, currency inconsistencies, country of origin declarations, address verification, Incoterms accuracy, and valuation issues. Each issue comes with a specific recommended fix.</p>
    </div>

    <div class="help-section">
      <h3>Important Notes</h3>
      <p>ClearDoc is a pre-submission review tool — it does not replace official customs filings or licensed customs broker services. Always verify findings with your compliance team or broker before making final corrections. Your documents are analyzed in real-time and are not stored on our servers.</p>
    </div>

  </div>

  <!-- Upload -->
  <div class="upload-card" id="uploadSection">
    <div class="drop-zone" id="dropZone">
      <input type="file" id="fileInput" accept=".pdf,.png,.jpg,.jpeg,.webp">
      <span class="drop-icon">📄</span>
      <div class="drop-title">Drop your document here</div>
      <div class="drop-sub">PDF, PNG, or JPG — up to 20MB</div>
    </div>

    <div class="file-selected" id="fileSelected">
      <span class="file-icon">📎</span>
      <span class="file-name" id="fileName"></span>
      <span style="color:var(--green);font-size:18px;">✓</span>
    </div>

    <button class="btn-check" id="checkBtn" disabled onclick="runCheck()">
      <span>⚡</span> Check Document
    </button>
  </div>

  <!-- Loading -->
  <div class="loading" id="loading">
    <div class="spinner"></div>
    <strong>Analyzing Document</strong>
    <p>Running customs compliance checks...</p>
  </div>

  <!-- Results -->
  <div id="results">
    <div class="status-banner" id="statusBanner">
      <div class="status-icon" id="statusIcon"></div>
      <div class="status-text">
        <div class="status-label" id="statusLabel"></div>
        <div class="status-title" id="statusTitle"></div>
        <div class="status-summary" id="statusSummary"></div>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card critical">
        <div class="stat-number" id="criticalCount">0</div>
        <div class="stat-label">Critical</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-number" id="warningCount">0</div>
        <div class="stat-label">Warnings</div>
      </div>
      <div class="stat-card passed">
        <div class="stat-number" id="passedCount">0</div>
        <div class="stat-label">Passed</div>
      </div>
    </div>

    <div id="issuesSection"></div>
    <div id="passedSection"></div>

    <div class="recommendation-card">
      <div class="rec-label">Recommendation</div>
      <p id="recommendation"></p>
    </div>

    <button class="btn-reset" onclick="resetForm()">← Check Another Document</button>
  </div>
</div>

<footer>ClearDoc &nbsp;·&nbsp; Powered by Claude AI &nbsp;·&nbsp; For compliance review purposes only</footer>

<script>
  const fileInput = document.getElementById('fileInput');
  const dropZone = document.getElementById('dropZone');
  const fileSelected = document.getElementById('fileSelected');
  const fileName = document.getElementById('fileName');
  const checkBtn = document.getElementById('checkBtn');
  let selectedFile = null;

  fileInput.addEventListener('change', e => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  });

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });

  function setFile(file) {
    selectedFile = file;
    fileName.textContent = file.name;
    fileSelected.classList.add('visible');
    checkBtn.disabled = false;
  }

  async function runCheck() {
    if (!selectedFile) return;

    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('loading').classList.add('visible');
    document.getElementById('results').classList.remove('visible');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch('/check', { method: 'POST', body: formData });
      const data = await res.json();
      document.getElementById('loading').classList.remove('visible');
      if (data.error) {
        alert('Error: ' + data.error);
        resetForm();
      } else {
        renderResults(data);
      }
    } catch (err) {
      alert('Something went wrong. Please try again.');
      resetForm();
    }
  }

  function renderResults(data) {
    const status = data.overall_status || 'UNKNOWN';
    const icons = { HOLD: '🚫', WARNING: '⚠️', CLEAR: '✅' };
    const titles = { HOLD: 'Document on Hold', WARNING: 'Review Required', CLEAR: 'Cleared for Shipment' };

    const banner = document.getElementById('statusBanner');
    banner.className = 'status-banner ' + status;
    document.getElementById('statusIcon').textContent = icons[status] || '❓';
    document.getElementById('statusLabel').textContent = status;
    document.getElementById('statusTitle').textContent = titles[status] || status;
    document.getElementById('statusSummary').textContent = data.summary || '';

    const issues = data.issues || [];
    const critical = issues.filter(i => i.severity === 'CRITICAL').length;
    const warnings = issues.filter(i => i.severity === 'WARNING').length;
    document.getElementById('criticalCount').textContent = critical;
    document.getElementById('warningCount').textContent = warnings;
    document.getElementById('passedCount').textContent = (data.passed_checks || []).length;

    // Issues
    const issuesSection = document.getElementById('issuesSection');
    if (issues.length > 0) {
      let html = `<div class="section-title">⚠ Issues Found (${issues.length})</div>`;
      issues.forEach((issue, i) => {
        html += `
          <div class="issue-card ${issue.severity}" onclick="toggleIssue(${i})">
            <div class="issue-header">
              <div class="severity-dot"></div>
              <span class="severity-badge">${issue.severity}</span>
              <span class="issue-field">${issue.field}</span>
              <span class="issue-toggle">▾</span>
            </div>
            <div class="issue-body">
              <div class="issue-row">
                <span class="issue-row-label">Issue</span>
                <span class="issue-row-value">${issue.issue}</span>
                <span class="issue-row-label">Location</span>
                <span class="issue-row-value">${issue.location}</span>
                <span class="issue-row-label">Fix</span>
                <span class="fix-value">${issue.fix}</span>
              </div>
            </div>
          </div>`;
      });
      issuesSection.innerHTML = html;
    }

    // Passed checks
    const passed = data.passed_checks || [];
    if (passed.length > 0) {
      let html = `<div class="section-title" style="margin-top:24px;">✓ Passed Checks (${passed.length})</div><div class="passed-grid">`;
      passed.forEach(check => { html += `<div class="passed-item">${check}</div>`; });
      html += '</div>';
      document.getElementById('passedSection').innerHTML = html;
    }

    document.getElementById('recommendation').textContent = data.recommendation || '';
    document.getElementById('results').classList.add('visible');
  }

  function toggleIssue(i) {
    const cards = document.querySelectorAll('.issue-card');
    cards[i].classList.toggle('open');
  }

  function toggleHelp() {
    const panel = document.getElementById('helpPanel');
    const toggle = document.getElementById('helpToggle');
    panel.classList.toggle('visible');
    toggle.classList.toggle('open');
  }

  function resetForm() {
    selectedFile = null;
    fileInput.value = '';
    fileSelected.classList.remove('visible');
    checkBtn.disabled = true;
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('loading').classList.remove('visible');
    document.getElementById('results').classList.remove('visible');
    document.getElementById('issuesSection').innerHTML = '';
    document.getElementById('passedSection').innerHTML = '';
  }
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/check", methods=["POST"])
def check():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PDF, PNG, or JPG."}), 400

    try:
        file_bytes = file.read()
        filename = secure_filename(file.filename)
        result = check_document(file_bytes, filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    print(f"\nClearDoc running at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
