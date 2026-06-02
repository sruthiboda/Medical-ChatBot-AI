from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree
import json
import os
import re
import textwrap
import time


def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
load_env_file(os.path.join(ROOT_DIR, ".env.local"))
load_env_file(os.path.join(ROOT_DIR, ".env"))
load_env_file(os.path.join(BACKEND_DIR, ".env.local"))
load_env_file(os.path.join(BACKEND_DIR, ".env"))
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EMAIL = os.environ.get("NCBI_EMAIL", "demo@example.com")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
UNKNOWN_RESPONSE = "I do not know. The retrieved trusted sources do not provide enough evidence to answer this question."

TRUSTED_JOURNAL_HINTS = (
    "lancet",
    "bmj",
    "nature",
    "nejm",
    "jama",
    "american heart association",
    "circulation",
    "journal of the american heart association",
    "pubmed",
)

TRUSTED_SOURCES = [
    {
        "name": "PubMed",
        "filter": "",
        "website": "https://pubmed.ncbi.nlm.nih.gov/",
    },
    {
        "name": "Nature journals",
        "filter": '("Nature"[Journal] OR "Nat Med"[Journal] OR "Nat Rev Cardiol"[Journal] OR "Nat Rev Drug Discov"[Journal] OR "Nat Commun"[Journal])',
        "website": "https://www.nature.com/",
    },
    {
        "name": "American Heart Association journals",
        "filter": '("Circulation"[Journal] OR "J Am Heart Assoc"[Journal] OR "Stroke"[Journal] OR "Hypertension"[Journal] OR "Arterioscler Thromb Vasc Biol"[Journal] OR "Circ Res"[Journal])',
        "website": "https://www.ahajournals.org/",
    },
    {
        "name": "BMJ journals",
        "filter": '("BMJ"[Journal] OR "BMJ Open"[Journal] OR "Heart"[Journal] OR "Gut"[Journal] OR "Ann Rheum Dis"[Journal])',
        "website": "https://www.bmj.com/",
    },
    {
        "name": "The Lancet journals",
        "filter": '("Lancet"[Journal] OR "Lancet Neurol"[Journal] OR "Lancet Oncol"[Journal] OR "Lancet Diabetes Endocrinol"[Journal] OR "Lancet Respir Med"[Journal] OR "Lancet Infect Dis"[Journal])',
        "website": "https://www.thelancet.com/",
    },
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "give",
    "after", "have", "how", "in", "is", "it", "latest", "me", "of", "on", "or", "patient",
    "recent", "study", "studies", "the", "this", "to", "what", "with",
    "according", "additional", "arrives", "considered", "common", "current",
    "develops", "do", "does", "evidence", "linking", "old", "requires",
    "despite", "gradually", "investigated", "losing", "should", "standard",
    "symptom", "symptoms", "taking", "types", "various", "vision", "work",
    "year",
}

SAFETY_TERMS = {
    "adverse", "contraindication", "contraindications", "toxicity", "toxicities",
    "safety", "side", "effects", "effect", "warning", "warnings", "renal",
    "kidney", "lactic", "acidosis", "pregnancy", "hypersensitivity",
}

SAFETY_TRIGGER_TERMS = {
    "adverse", "contraindication", "contraindications", "toxicity", "toxicities",
    "safety", "side", "effects", "effect", "warning", "warnings", "lactic",
    "acidosis", "hypersensitivity",
}

KNOWN_DRUGS = {
    "metformin", "aspirin", "insulin", "atorvastatin", "statin",
    "semaglutide", "warfarin", "apixaban", "rivaroxaban", "dabigatran",
    "clopidogrel", "amlodipine", "lisinopril",
}

INTENT_TERMS = {
    "treatment", "treatments", "diagnosis", "diagnostic", "differential",
    "adverse", "contraindication", "contraindications", "intervention",
    "interventions", "management", "safety", "side", "effects", "toxicity",
    "guideline", "guidelines", "therapy", "therapies",
}

TREATMENT_QUERY_TERMS = {
    "intervention", "interventions", "optimization", "prioritized", "treatment",
    "treatments", "therapy", "therapies", "management", "guideline", "guidelines",
}

TREATMENT_EVIDENCE_TERMS = {
    "therapy", "therapies", "treatment", "treatments", "guideline-directed",
    "guideline directed", "pharmacological", "drug", "drugs", "medication",
    "medications", "sglt2", "sodium-glucose", "sacubitril", "valsartan",
    "arni", "ace inhibitor", "angiotensin", "beta-blocker", "beta blocker",
    "mineralocorticoid", "mra", "spironolactone", "eplerenone", "finerenone",
    "vericiguat", "ivabradine", "natriuretic peptide", "thrombolysis",
    "thrombolytic", "alteplase", "tenecteplase", "thrombectomy",
}

SYMPTOM_HINTS = {
    "pain", "fever", "cough", "swelling", "redness", "shortness",
    "headache", "chest", "nausea", "dizziness",
}

LOW_SIGNAL_TERMS = {
    "chest", "pain", "problem", "issue", "symptom", "symptoms", "disease",
    "treatment", "therapy", "management", "drug", "diagnosis", "latest",
    "recent", "study", "research",
}

QUESTION_NOISE_TERMS = STOPWORDS | INTENT_TERMS | {
    "patient", "patients", "adult", "adults", "child", "man", "woman",
    "question", "answer", "evidence", "based", "currently", "standard",
    "therapy", "therapies", "treatment", "treatments", "management",
}


class MedicalRagHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def translate_path(self, path):
        parsed_path = unquote(urlparse(path).path)
        if parsed_path.startswith("/docs/"):
            relative_path = parsed_path.removeprefix("/docs/").lstrip("/")
            return os.path.join(DOCS_DIR, relative_path.replace("/", os.sep))
        return super().translate_path(path)

    def do_POST(self):
        if self.path != "/api/ask":
            self.send_error(404)
            return

        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, status=400)
            return

        query = str(payload.get("query", "")).strip()
        if len(query) < 4:
            self.send_json({"answer": "Please enter a more specific medical question.", "sources": []})
            return

        started = time.time()
        try:
            result = run_agentic_workflow(query)
            result["latency_ms"] = int((time.time() - started) * 1000)
            self.send_json(result)
        except Exception as exc:
            self.send_json(
                {
                    "answer": UNKNOWN_RESPONSE,
                    "sources": [],
                    "workflow": [{"agent": "system", "status": "failed", "detail": str(exc)}],
                },
                status=200,
            )

    def send_json(self, data, status=200):
        encoded = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_agentic_workflow(query):
    workflow = []
    understanding = understand_query(query)
    workflow.append({
        "agent": "query-understanding-agent",
        "status": "ok",
        "detail": f"{understanding['intent']} query with keywords: {', '.join(understanding['keywords'][:6])}",
    })

    clarification = clarification_prompt(understanding)
    if clarification:
        workflow.append({"agent": "clarification-agent", "status": "needs_input", "detail": clarification})
        return {
            "answer": clarification,
            "sources": [],
            "workflow": workflow,
            "confidence": "low",
        }

    deterministic_queries = build_query_candidates(query)
    gemini_query = rewrite_query_with_gemini(query, deterministic_queries[0])
    queries = [gemini_query] + deterministic_queries if gemini_query else deterministic_queries
    queries = dedupe_preserve_order([item for item in queries if item])
    normalized = queries[0]
    if gemini_query:
        workflow.append({"agent": "ai-query-rewriter-agent", "status": "ok", "detail": "AI rewrote the retrieval query before trusted-source API calls"})
    else:
        workflow.append({"agent": "ai-query-rewriter-agent", "status": "skipped", "detail": "No AI rewrite available; using deterministic clinical rewrite"})
    workflow.append({"agent": "clinical-query-rewriter-agent", "status": "ok", "detail": f"Built {len(queries)} retrieval query variants; primary: {normalized}"})

    pmids, source_by_pmid, source_reports = search_trusted_sources(queries, sort_by_date=wants_recent_evidence(query))
    for report in source_reports:
        workflow.append({
            "agent": "source-check-agent",
            "status": "ok",
            "detail": f"Checked {report['name']} ({report['website']}) and found {report['count']} PubMed-indexed records",
        })
    workflow.append({
        "agent": "retrieval-agent",
        "status": "ok",
        "detail": f"Retrieved {len(pmids)} unique records after step-by-step trusted-source checks",
    })

    papers = pubmed_fetch(pmids[:35], source_by_pmid)
    workflow.append({"agent": "ingestion-agent", "status": "ok", "detail": f"Parsed {len(papers)} abstracts"})

    evidence = validate_evidence(query, papers)
    workflow.append({"agent": "trusted-source-filter-agent", "status": "ok", "detail": f"{len(evidence)} trusted-source papers passed evidence checks"})

    evidence = evidence[:5]
    confidence_score = evidence_confidence(evidence)
    confidence_label = confidence_from_score(confidence_score)
    workflow.append({
        "agent": "relevance-ranking-agent",
        "status": "ok",
        "detail": f"Ranked {len(evidence)} papers with {round(confidence_score * 100)}% confidence",
    })

    can_answer = confidence_score >= 0.30 and len(evidence) >= 1
    workflow.append({
        "agent": "hallucination-guard-agent",
        "status": "ok" if can_answer else "blocked",
        "detail": "Evidence threshold met." if can_answer else "Insufficient direct evidence; refusing to answer.",
    })

    if not can_answer:
        return {
            "answer": UNKNOWN_RESPONSE,
            "sources": evidence,
            "workflow": workflow,
            "confidence": "low",
        }

    answer = synthesize_answer(query, evidence)
    if answer == UNKNOWN_RESPONSE:
        confidence_label = "low"
    workflow.append({"agent": "response-generation-agent", "status": "ok", "detail": "Generated a citation-grounded answer from accepted evidence"})
    workflow.append({"agent": "citation-agent", "status": "ok", "detail": f"Prepared {len(evidence)} visible citations"})

    return {
        "answer": answer,
        "sources": evidence,
        "workflow": workflow,
        "confidence": confidence_label,
    }


def normalize_query(query):
    terms = [token for token in re.findall(r"[A-Za-z0-9-]+", query.lower()) if token not in STOPWORDS]
    if not terms:
        return query
    if asks_crispr_retinal(query):
        return (
            '(CRISPR[Title/Abstract] OR "gene editing"[Title/Abstract] OR "base editing"[Title/Abstract]) '
            'AND ("inherited retinal degeneration"[Title/Abstract] OR "inherited retinal disease"[Title/Abstract] '
            'OR "retinal degeneration"[Title/Abstract] OR "Leber congenital amaurosis"[Title/Abstract]) '
            'AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR trial[Title/Abstract] '
            'OR review[Publication Type] OR clinical trial[Publication Type])'
        )
    if asks_mrna_therapeutics(query):
        return (
            '("mRNA therapy"[Title/Abstract] OR "mRNA therapeutics"[Title/Abstract] OR "messenger RNA"[Title/Abstract]) '
            'AND (therapy[Title/Abstract] OR therapeutics[Title/Abstract] OR treatment[Title/Abstract] '
            'OR cancer[Title/Abstract] OR "rare disease"[Title/Abstract] OR "protein replacement"[Title/Abstract]) '
            'AND (review[Publication Type] OR clinical trial[Publication Type] OR guideline[Publication Type])'
        )
    if asks_metformin_b12(query):
        return (
            '(metformin[Title/Abstract]) AND ("vitamin B12"[Title/Abstract] OR cobalamin[Title/Abstract]) '
            'AND (deficiency[Title/Abstract] OR malabsorption[Title/Abstract] OR neuropathy[Title/Abstract]) '
            'AND (review[Publication Type] OR clinical trial[Publication Type] OR meta-analysis[Publication Type] OR guideline[Publication Type])'
        )
    if asks_acute_stroke_intervention(query):
        return (
            '("acute ischemic stroke"[Title/Abstract] OR "acute stroke"[Title/Abstract]) '
            'AND (thrombolysis[Title/Abstract] OR alteplase[Title/Abstract] OR tenecteplase[Title/Abstract] '
            'OR thrombectomy[Title/Abstract] OR "endovascular therapy"[Title/Abstract] OR guideline[Publication Type])'
        )
    if asks_hfref_treatment(query):
        recency = ' AND ("2021"[Date - Publication] : "3000"[Date - Publication])' if wants_recent_evidence(query) else ""
        return (
            '("heart failure with reduced ejection fraction"[Title/Abstract] OR HFrEF[Title/Abstract]) '
            'AND ("guideline-directed medical therapy"[Title/Abstract] OR "guideline directed medical therapy"[Title/Abstract] '
            'OR "SGLT2"[Title/Abstract] OR "sacubitril"[Title/Abstract] OR "valsartan"[Title/Abstract] '
            'OR "beta-blocker"[Title/Abstract] OR "beta blocker"[Title/Abstract] OR "mineralocorticoid"[Title/Abstract] '
            'OR "pharmacological treatment"[Title/Abstract] OR guideline[Publication Type] OR review[Publication Type])'
            f"{recency}"
        )
    if asks_drug_safety(query):
        subjects = subject_terms(terms)
        if subjects:
            primary_subject = subjects[0]
            subject_clause = f'("{primary_subject}"[Title/Abstract] OR "{primary_subject}/adverse effects"[MeSH Terms] OR "{primary_subject}/contraindications"[MeSH Terms])'
            safety_clause = " OR ".join([
                '"adverse effects"[Subheading]',
                '"contraindications"[Subheading]',
                '"Drug-Related Side Effects and Adverse Reactions"[Mesh]',
                '"safety"[Title/Abstract]',
                '"contraindication"[Title/Abstract]',
                '"contraindications"[Title/Abstract]',
                '"toxicity"[Title/Abstract]',
            ])
            return f"({subject_clause}) AND ({safety_clause})"
    core_terms = important_terms(terms)[:6]
    if len(core_terms) >= 3:
        primary = " AND ".join(f'"{term}"[Title/Abstract]' for term in core_terms[:2])
        secondary = " OR ".join(f'"{term}"[Title/Abstract]' for term in core_terms[2:])
        core = f"({primary}) AND ({secondary})"
    else:
        core = " OR ".join(f'"{term}"[Title/Abstract]' for term in core_terms)
    return f"({core}) AND (review[Publication Type] OR clinical trial[Publication Type] OR guideline[Publication Type] OR meta-analysis[Publication Type])"


def build_query_candidates(query):
    primary = normalize_query(query)
    terms = important_terms([
        token for token in re.findall(r"[A-Za-z0-9-]+", query.lower())
        if token not in STOPWORDS
    ])
    candidates = [primary]

    phrases = extract_medical_phrases(query)
    if phrases:
        phrase_query = " OR ".join(f'"{phrase}"[Title/Abstract]' for phrase in phrases[:5])
        candidates.append(f"({phrase_query}) AND (review[Publication Type] OR clinical trial[Publication Type] OR guideline[Publication Type] OR meta-analysis[Publication Type])")

    if terms:
        broad = " OR ".join(f'"{term}"[Title/Abstract]' for term in terms[:8])
        candidates.append(f"({broad}) AND (review[Publication Type] OR clinical trial[Publication Type] OR guideline[Publication Type] OR meta-analysis[Publication Type])")
        candidates.append(" ".join(terms[:8]))

    return dedupe_preserve_order(candidates)


def extract_medical_phrases(query):
    query_lower = query.lower()
    known = [
        "heart failure with reduced ejection fraction",
        "heart failure",
        "chronic kidney disease",
        "type 2 diabetes",
        "acute ischemic stroke",
        "sickle cell disease",
        "inherited retinal degeneration",
        "inherited retinal disease",
        "retinal degeneration",
        "vitamin b12 deficiency",
        "mrna therapy",
        "mrna therapeutics",
        "crispr",
        "metformin",
    ]
    phrases = [phrase for phrase in known if phrase in query_lower]
    capitalized = re.findall(r"\b[A-Z][A-Za-z0-9-]{2,}\b", query)
    phrases.extend(item.lower() for item in capitalized if item.lower() not in STOPWORDS)
    return dedupe_preserve_order(phrases)


def dedupe_preserve_order(items):
    seen = set()
    output = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def understand_query(query):
    normalized = query.strip().lower()
    keywords = [
        token for token in re.findall(r"[a-z0-9-]+", normalized)
        if len(token) > 2 and token not in STOPWORDS
    ]
    if asks_drug_safety(query) or any(drug in normalized for drug in ("metformin", "aspirin", "insulin", "statin")):
        intent = "drug_query"
    elif asks_treatment(query):
        intent = "treatment_query"
    elif "diagnos" in normalized or "differential" in normalized:
        intent = "diagnosis_query"
    elif any(term in normalized for term in ("latest", "recent", "study", "evidence", "research")):
        intent = "research_query"
    elif any(term in keywords for term in SYMPTOM_HINTS):
        intent = "symptom_query"
    else:
        intent = "research_query"
    return {
        "intent": intent,
        "keywords": keywords,
        "is_vague": intent == "symptom_query" and len([t for t in keywords if t not in LOW_SIGNAL_TERMS]) <= 1,
    }


def clarification_prompt(understanding):
    if not understanding["is_vague"]:
        return ""
    return (
        "Please add more clinical detail before I search: patient age, duration, "
        "key symptoms, relevant history, and what you want to know."
    )


def wants_recent_evidence(query):
    return any(word in query.lower() for word in ("latest", "recent", "new", "current", "2025", "2026"))


def asks_drug_safety(query):
    tokens = set(re.findall(r"[a-z0-9-]+", query.lower()))
    return bool(tokens & SAFETY_TRIGGER_TERMS)


def asks_treatment(query):
    tokens = set(re.findall(r"[a-z0-9-]+", query.lower()))
    return bool(tokens & TREATMENT_QUERY_TERMS)


def asks_hfref_treatment(query):
    query_lower = query.lower()
    return asks_treatment(query) and (
        "heart failure with reduced ejection fraction" in query_lower
        or "hfref" in query_lower
        or all(term in query_lower for term in ("heart failure", "reduced", "ejection"))
        or ("heart failure" in query_lower and "beta-blocker" in query_lower)
    )


def subject_terms(terms):
    return [term for term in terms if term not in SAFETY_TERMS and term not in INTENT_TERMS and len(term) > 2]


def important_terms(terms):
    noisy = {
        "65", "68", "30", "hours", "man", "child", "patient", "patients",
        "adult", "adults", "diseases", "currently", "being", "beyond",
        "vaccines", "experimental",
    }
    return [term for term in terms if term not in noisy and len(term) > 2]


def asks_crispr_retinal(query):
    query_lower = query.lower()
    return ("crispr" in query_lower or "gene editing" in query_lower) and (
        "retinal" in query_lower or "vision" in query_lower or "inherited retinal" in query_lower
    )


def asks_mrna_therapeutics(query):
    query_lower = query.lower()
    return ("mrna" in query_lower or "messenger rna" in query_lower) and (
        "therap" in query_lower or "disease" in query_lower or "beyond vaccines" in query_lower
    )


def asks_metformin_b12(query):
    query_lower = query.lower()
    return "metformin" in query_lower and ("b12" in query_lower or "cobalamin" in query_lower)


def asks_acute_stroke_intervention(query):
    query_lower = query.lower()
    return "stroke" in query_lower and (
        "intervention" in query_lower
        or "interventions" in query_lower
        or "onset" in query_lower
        or "emergency" in query_lower
    )


def search_trusted_sources(base_queries, sort_by_date=False):
    if isinstance(base_queries, str):
        base_queries = [base_queries]
    unique_pmids = []
    seen = set()
    source_by_pmid = {}
    report_map = {source["name"]: {"name": source["name"], "website": source["website"], "count": 0} for source in TRUSTED_SOURCES}

    for source in TRUSTED_SOURCES:
        source_seen = set()
        for base_query in base_queries[:4]:
            source_query = base_query
            if source["filter"]:
                source_query = f"({base_query}) AND {source['filter']}"
            try:
                pmids = pubmed_search(source_query, sort_by_date=sort_by_date, retmax=10)
            except Exception:
                pmids = []
            source_seen.update(pmids)
            for pmid in pmids:
                source_by_pmid.setdefault(pmid, source["name"])
                if pmid in seen:
                    continue
                seen.add(pmid)
                unique_pmids.append(pmid)
        report_map[source["name"]]["count"] = len(source_seen)

    return unique_pmids, source_by_pmid, list(report_map.values())


def pubmed_search(term, sort_by_date=False, retmax=12):
    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": str(retmax),
        "sort": "pub date" if sort_by_date else "relevance",
        "email": EMAIL,
    }
    data = fetch_json(f"{NCBI_BASE}/esearch.fcgi?{urlencode(params)}")
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_fetch(pmids, source_by_pmid=None):
    if not pmids:
        return []
    source_by_pmid = source_by_pmid or {}
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "email": EMAIL,
    }
    xml_text = fetch_text(f"{NCBI_BASE}/efetch.fcgi?{urlencode(params)}")
    root = ElementTree.fromstring(xml_text)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        pmid = text_at(article, ".//PMID")
        title = clean_text(text_at(article, ".//ArticleTitle"))
        journal = clean_text(text_at(article, ".//Journal/Title"))
        year = text_at(article, ".//PubDate/Year") or text_at(article, ".//PubDate/MedlineDate")[:4]
        doi = article_id(article, "doi")
        abstract_parts = [clean_text("".join(node.itertext())) for node in article.findall(".//Abstract/AbstractText")]
        abstract = clean_text(" ".join(part for part in abstract_parts if part))
        if not abstract:
            continue
        papers.append(
            {
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "year": year,
                "abstract": abstract,
                "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source": source_by_pmid.get(pmid, classify_source(journal)),
            }
        )
    return papers


def validate_evidence(query, papers):
    query_terms = [t for t in re.findall(r"[a-z0-9-]+", query.lower()) if t not in STOPWORDS and len(t) > 2]
    focus_terms = question_focus_terms(query)
    subjects = subject_terms(query_terms)
    primary_subject = primary_subject_term(query, subjects)
    requires_safety = asks_drug_safety(query)
    requires_treatment = asks_treatment(query)
    scored = []
    for paper in papers:
        haystack = f"{paper['title']} {paper['journal']} {paper['abstract']}".lower()
        if requires_safety and primary_subject and primary_subject not in haystack:
            continue
        focus_score = focus_match_score(focus_terms, haystack)
        if focus_terms and focus_score < minimum_focus_score(focus_terms):
            continue
        safety_sentence = ""
        if requires_safety:
            safety_sentence = matching_safety_sentence(paper, primary_subject)
        if requires_safety and not safety_sentence:
            continue
        treatment_sentence = ""
        if requires_treatment:
            treatment_sentence = matching_treatment_sentence(paper, query)
        overlap = sum(1 for term in query_terms if term in haystack)
        trusted_bonus = 1 if any(hint in paper["journal"].lower() for hint in TRUSTED_JOURNAL_HINTS) else 0
        safety_bonus = 3 if safety_sentence else 0
        treatment_bonus = 3 if treatment_sentence else 0
        direct_sentence = best_relevant_sentence(paper, query)
        direct_bonus = 3 if direct_sentence else 0
        score = overlap + trusted_bonus + safety_bonus + treatment_bonus + direct_bonus + focus_score
        minimum_score = 2 if (requires_safety or requires_treatment) else 1
        if score < minimum_score:
            continue
        snippet = safety_sentence or treatment_sentence or direct_sentence or best_snippet(paper["abstract"], query_terms)
        scored.append(
            {
                "pmid": paper["pmid"],
                "title": paper["title"],
                "journal": paper["journal"],
                "year": paper["year"],
                "url": paper["url"],
                "source": paper["source"],
                "evidence": snippet,
                "score": score,
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)


def question_focus_terms(query):
    terms = []
    for token in re.findall(r"[a-z0-9-]+", query.lower()):
        if len(token) <= 2 or token in QUESTION_NOISE_TERMS:
            continue
        if re.fullmatch(r"\d+", token):
            continue
        terms.append(token)
    return dedupe_preserve_order(terms)


def minimum_focus_score(focus_terms):
    if len(focus_terms) <= 2:
        return 1
    if len(focus_terms) <= 5:
        return 2
    return 3


def focus_match_score(focus_terms, text):
    if not focus_terms:
        return 0
    return sum(1 for term in focus_terms if term in text)


def best_relevant_sentence(paper, query):
    focus_terms = question_focus_terms(query)
    if not focus_terms:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", f"{paper['title']}. {paper['abstract']}")
    best_sentence = ""
    best_score = 0
    for sentence in sentences:
        sentence_lower = sentence.lower()
        score = focus_match_score(focus_terms, sentence_lower)
        if score > best_score:
            best_score = score
            best_sentence = sentence
    if best_score < minimum_focus_score(focus_terms):
        return ""
    return textwrap.shorten(clean_text(best_sentence), width=280, placeholder="...")


def matching_safety_sentence(paper, primary_subject):
    text = f"{paper['title']}. {paper['abstract']}"
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence_lower = sentence.lower()
        if primary_subject in sentence_lower and any(term in sentence_lower for term in SAFETY_TERMS):
            return textwrap.shorten(clean_text(sentence), width=280, placeholder="...")
    return ""


def primary_subject_term(query, subjects):
    tokens = re.findall(r"[a-z0-9-]+", query.lower())
    for token in tokens:
        if token in KNOWN_DRUGS:
            return token
    return subjects[0] if subjects else ""


def matching_treatment_sentence(paper, query):
    query_lower = query.lower()
    text = f"{paper['title']}. {paper['abstract']}"
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence_lower = sentence.lower()
        has_treatment = any(term in sentence_lower for term in TREATMENT_EVIDENCE_TERMS)
        if not has_treatment:
            continue
        full_text_lower = text.lower()
        paper_matches_hfref = (
            "reduced ejection fraction" in full_text_lower
            or "hfref" in full_text_lower
            or ("heart failure" in full_text_lower and "ejection fraction" in full_text_lower)
        )
        if asks_hfref_treatment(query) and not paper_matches_hfref:
            continue
        if "preserved ejection fraction" in sentence_lower and "reduced ejection fraction" not in sentence_lower:
            continue
        return textwrap.shorten(clean_text(sentence), width=280, placeholder="...")
    return ""


def evidence_confidence(evidence):
    if not evidence:
        return 0
    top = evidence[:3]
    avg_score = sum(item.get("score", 0) for item in top) / max(len(top), 1)
    source_diversity = len({item.get("source", "") for item in evidence}) / 5
    count_signal = min(len(evidence) / 5, 1)
    normalized_score = min(avg_score / 9, 1)
    return min(1, normalized_score * 0.55 + count_signal * 0.3 + source_diversity * 0.15)


def confidence_from_score(score):
    if score >= 0.72:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def best_snippet(abstract, terms):
    sentences = re.split(r"(?<=[.!?])\s+", abstract)
    ranked = sorted(
        sentences,
        key=lambda sentence: sum(1 for term in terms if term in sentence.lower()),
        reverse=True,
    )
    snippet = ranked[0] if ranked else abstract
    return textwrap.shorten(snippet, width=280, placeholder="...")


def synthesize_answer(query, evidence):
    gemini_answer = synthesize_with_gemini(query, evidence)
    if gemini_answer:
        return clean_answer(gemini_answer)
    if OPENAI_API_KEY:
        llm_answer = synthesize_with_openai(query, evidence)
        if llm_answer:
            return clean_answer(llm_answer)
    return synthesize_extractively(query, evidence)


def rewrite_query_with_gemini(question, deterministic_query):
    if not GEMINI_API_KEY:
        return ""
    prompt = (
        "Rewrite this clinician question into a PubMed ESearch query. "
        "Return only the query string, no explanation, no medical answer. "
        "Preserve the clinical meaning and prefer Title/Abstract terms, guidelines, reviews, clinical trials, or meta-analyses. "
        "Do not invent diagnoses or treatments not present in the question.\n\n"
        f"Question: {question}\n"
        f"Safe fallback query: {deterministic_query}"
    )
    text = call_gemini(prompt, max_tokens=180)
    if not text:
        return ""
    candidate = text.strip().strip("`").strip()
    if len(candidate) < 8 or len(candidate) > 900:
        return ""
    if any(blocked in candidate.lower() for blocked in ("answer:", "i don't know", "citation", "\n\n")):
        return ""
    return candidate


def synthesize_with_gemini(query, evidence):
    if not GEMINI_API_KEY:
        return None
    sources = "\n\n".join(
        f"[{idx + 1}] Title: {src['title']}\nJournal: {src['journal']} ({src['year']})\n"
        f"Source: {src['source']}\nPMID: {src['pmid']}\nEvidence: {src['evidence']}"
        for idx, src in enumerate(evidence[:5])
    )
    prompt = clinical_synthesis_prompt(query, sources)
    answer = call_gemini(prompt, max_tokens=700)
    if not answer:
        return None
    answer = answer.strip().replace("\r\n", "\n")
    if "i don't know" in answer.lower() or "i do not know" in answer.lower():
        return UNKNOWN_RESPONSE
    return answer


def clinical_synthesis_prompt(question, accepted_papers):
    return (
        "You are a Clinical Evidence Synthesis Agent.\n\n"
        "Use ONLY accepted evidence.\n\n"
        f"Question:\n{question}\n\n"
        f"Evidence:\n{accepted_papers}\n\n"
        "Requirements:\n\n"
        "1. Answer the user's exact question.\n"
        "2. Do not include information unrelated to the question.\n"
        "3. Ignore evidence that discusses different topics.\n"
        f"4. If evidence is insufficient say:\n\n\"{UNKNOWN_RESPONSE}\"\n\n"
        "5. For drug safety questions always structure:\n\n"
        "- Common adverse effects\n"
        "- Serious adverse effects\n"
        "- Contraindications\n"
        "- Monitoring recommendations\n\n"
        "6. Cite supporting papers inline like [1].\n\n"
        "Never answer from general disease knowledge.\n"
        "Use only retrieved evidence."
    )


def call_gemini(prompt, max_tokens=220):
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.2,
            "maxOutputTokens": max_tokens,
        },
    }
    req = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        data = json.loads(urlopen(req, timeout=30).read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    chunks = []
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            chunks.append(part.get("text", ""))
    return "".join(chunks).strip() or None


def synthesize_with_openai(query, evidence):
    sources = "\n".join(
        f"[{idx + 1}] {src['title']} ({src['journal']}, {src['year']}): {src['evidence']}"
        for idx, src in enumerate(evidence[:5])
    )
    prompt = (
        clinical_synthesis_prompt(query, sources)
    )
    body = {
        "model": OPENAI_MODEL,
        "input": prompt,
        "temperature": 0,
        "max_output_tokens": 700,
    }
    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"authorization": f"Bearer {OPENAI_API_KEY}", "content-type": "application/json"},
        method="POST",
    )
    try:
        data = json.loads(urlopen(req, timeout=25).read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return extract_openai_text(data)


def synthesize_extractively(query, evidence):
    if asks_drug_safety(query):
        return synthesize_drug_safety_answer(query, evidence)
    focused = synthesize_focused_answer(evidence)
    if focused:
        return clean_answer(focused)
    answer = synthesize_general_answer(query, evidence)
    return clean_answer(answer) if answer else UNKNOWN_RESPONSE


def synthesize_general_answer(query, evidence):
    claims = []
    for idx, src in enumerate(evidence[:3], start=1):
        sentence = best_answer_sentence(src, query) or src["evidence"].strip()
        sentence = re.sub(r"\s+", " ", sentence)
        if not sentence or sentence.lower() == src["title"].lower().strip("."):
            sentence = src["title"].strip()
        claims.append(f"{sentence} [{idx}]")
    return " ".join(claims)


def best_answer_sentence(source, query):
    focus_terms = question_focus_terms(query)
    text = source.get("evidence", "")
    if not text:
        return ""
    candidates = re.split(r"(?<=[.!?])\s+", text)
    best = ""
    best_score = 0
    for sentence in candidates:
        score = focus_match_score(focus_terms, sentence.lower())
        if score > best_score:
            best = sentence
            best_score = score
    if focus_terms and best_score < 1:
        return ""
    return best


def synthesize_drug_safety_answer(query, evidence):
    focus_terms = subject_terms(question_focus_terms(query))
    primary_subject = primary_subject_term(query, focus_terms)
    buckets = {
        "Common adverse effects": [],
        "Serious adverse effects": [],
        "Contraindications": [],
        "Monitoring recommendations": [],
    }
    for idx, src in enumerate(evidence[:5], start=1):
        text = f"{src['title']}. {src['evidence']}"
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence_clean = clean_text(sentence)
            sentence_lower = sentence_clean.lower()
            if not sentence_clean:
                continue
            if primary_subject and primary_subject not in sentence_lower:
                continue
            citation = f"{sentence_clean} [{idx}]"
            if any(term in sentence_lower for term in ("gastrointestinal", "nausea", "diarrhea", "abdominal", "vitamin b12", "b12 deficiency")):
                buckets["Common adverse effects"].append(citation)
            if any(term in sentence_lower for term in ("serious", "lactic acidosis", "toxicity", "severe", "hypoglycemia")):
                buckets["Serious adverse effects"].append(citation)
            pregnancy_contra = "pregnancy" in sentence_lower and any(term in sentence_lower for term in ("contraindication", "contraindicated"))
            if pregnancy_contra or any(term in sentence_lower for term in ("renal", "kidney", "hypersensitivity", "lactic acidosis", "acidosis")):
                buckets["Contraindications"].append(citation)
            if any(term in sentence_lower for term in ("monitor", "monitoring", "renal function", "kidney function", "vitamin b12", "b12")):
                buckets["Monitoring recommendations"].append(citation)

    lines = []
    for heading, values in buckets.items():
        if values:
            lines.append(f"{heading}: {values[0]}")
        else:
            lines.append(f"{heading}: Not specified in accepted evidence.")
    specified_count = sum(1 for line in lines if "Not specified" not in line)
    if specified_count == 0:
        return UNKNOWN_RESPONSE
    return "\n".join(lines)


def synthesize_focused_answer(evidence):
    text = " ".join(f"{src['title']} {src['evidence']}" for src in evidence).lower()
    claims = []

    if "metformin" in text and ("vitamin b12" in text or "cobalamin" in text):
        claims.append("Retrieved evidence links prolonged metformin use with vitamin B12 deficiency")
        if "neuropathy" in text:
            claims.append("neuropathy-related concern is reported in the retrieved evidence")
        return cite_claims(claims, evidence)

    if "acute ischemic stroke" in text or "acute stroke" in text:
        if any(term in text for term in ("alteplase", "tenecteplase", "thrombolysis")):
            claims.append("For eligible acute ischemic stroke patients, urgent IV thrombolysis is supported")
        if any(term in text for term in ("thrombectomy", "endovascular therapy")):
            claims.append("mechanical thrombectomy/endovascular therapy should be considered when indicated")
        if claims:
            return cite_claims(claims, evidence)

    if "heart failure" in text:
        if any(term in text for term in ("sglt2", "sodium-glucose", "canagliflozin", "dapagliflozin", "empagliflozin")):
            claims.append("Evidence supports considering an SGLT2 inhibitor in heart failure care")
        if any(term in text for term in ("sacubitril", "valsartan", "natriuretic peptide")):
            claims.append("therapies targeting the natriuretic peptide system may reduce heart-failure events")
        if any(term in text for term in ("spironolactone", "eplerenone", "mineralocorticoid", "mra", "finerenone")):
            claims.append("mineralocorticoid-receptor antagonist therapy appears in the retrieved evidence")
        if claims:
            return cite_claims(claims, evidence)

    if any(term in text for term in ("crispr", "gene editing", "gene therapy", "base editing", "prime editing")) and (
        "retinal" in text or "vision" in text or "amaurosis" in text or "stargardt" in text
    ):
        claims.append("Retrieved evidence describes gene therapy or gene-editing approaches being investigated for inherited retinal diseases")
        if any(term in text for term in ("prime editing", "base editing", "crispr")):
            claims.append("the approaches include CRISPR-related, base-editing, or prime-editing strategies")
        if any(term in text for term in ("leber", "cep290", "stargardt", "retinitis pigmentosa", "rpe65")):
            claims.append("studied inherited retinal targets include Leber congenital amaurosis, Stargardt disease, retinitis pigmentosa, or RPE65-related disease")
        return cite_claims(claims, evidence)

    if ("mrna" in text or "messenger rna" in text) and any(term in text for term in ("therapy", "therapeutics", "treatment")):
        claims.append("Retrieved evidence describes mRNA therapeutics beyond vaccines as a platform for delivering therapeutic proteins or immune targets")
        if any(term in text for term in ("cancer", "oncology", "tumor")):
            claims.append("cancer is one investigated disease area")
        if any(term in text for term in ("rare disease", "protein replacement", "genetic")):
            claims.append("rare or genetic disease applications are also discussed")
        return cite_claims(claims, evidence)

    return ""


def cite_claims(claims, evidence):
    cited = []
    for claim in claims[:3]:
        idx = citation_for_claim(claim, evidence)
        cited.append(f"{claim[:1].upper() + claim[1:]} [{idx}].")
    return " ".join(cited)


def citation_for_claim(claim, evidence):
    claim_terms = {term for term in re.findall(r"[a-z0-9-]+", claim.lower()) if len(term) > 3}
    best_idx = 1
    best_score = -1
    for idx, src in enumerate(evidence[:5], start=1):
        haystack = f"{src['title']} {src['evidence']}".lower()
        score = sum(1 for term in claim_terms if term in haystack)
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx


def clean_answer(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_openai_text(data):
    chunks = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in ("output_text", "text"):
                chunks.append(content.get("text", ""))
    return " ".join(chunks).strip()


def fetch_json(url):
    return json.loads(fetch_text(url))


def fetch_text(url):
    req = Request(url, headers={"user-agent": f"ClinicalEvidenceRAG/0.1 ({EMAIL})"})
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def text_at(node, path):
    match = node.find(path)
    if match is None or match.text is None:
        return ""
    return match.text.strip()


def article_id(node, id_type):
    for match in node.findall(".//ArticleId"):
        if match.attrib.get("IdType") == id_type and match.text:
            return match.text.strip()
    return ""


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def classify_source(journal):
    journal_lower = journal.lower()
    for source in TRUSTED_SOURCES[1:]:
        if source["name"].split()[0].lower() in journal_lower:
            return source["name"]
    if "circulation" in journal_lower or "heart assoc" in journal_lower or "stroke" == journal_lower:
        return "American Heart Association journals"
    if "bmj" in journal_lower:
        return "BMJ journals"
    if "lancet" in journal_lower:
        return "The Lancet journals"
    if "nature" in journal_lower or journal_lower.startswith("nat "):
        return "Nature journals"
    return "PubMed"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), MedicalRagHandler)
    print(f"Clinical Evidence RAG running at http://127.0.0.1:{port}")
    server.serve_forever()
