const { useMemo, useState } = React;
const h = React.createElement;

const unknownResponse = "I do not know. The retrieved trusted sources do not provide enough evidence to answer this question.";

const examples = [
  ["Pregnancy", "A pregnant patient has severe hypertension and headache at 32 weeks. What evidence-based management should be considered?"],
  ["COPD", "A patient with COPD has frequent exacerbations despite inhaler therapy. What treatments reduce exacerbations?"],
  ["CRISPR", "A child with inherited retinal degeneration is gradually losing vision despite standard treatment. What experimental CRISPR-based therapies are being investigated?"],
  ["mRNA", "How do mRNA therapies work beyond vaccines, and what diseases are currently being investigated?"],
  ["AFib", "A 70-year-old patient with atrial fibrillation has high stroke risk. What anticoagulation options are supported by evidence?"],
  ["Metformin", "What are the adverse effects and contraindications of metformin in adults with type 2 diabetes?"]
];

const initialWorkflow = [
  { agent: "QueryUnderstandingAgent", detail: "Waiting for an incoming medical question" },
  { agent: "ClarificationAgent", detail: "Checks whether more detail is needed" },
  { agent: "ClinicalQueryRewriterAgent", detail: "Builds retrieval-ready medical queries" },
  { agent: "RetrievalAgent", detail: "Searches trusted medical literature" },
  { agent: "TrustedSourceFilterAgent", detail: "Filters weak or irrelevant evidence" },
  { agent: "RelevanceRankingAgent", detail: "Ranks accepted sources" },
  { agent: "HallucinationGuardAgent", detail: "Blocks weak evidence before answering" },
  { agent: "ResponseGenerationAgent", detail: "Generates an answer from accepted evidence" },
  { agent: "CitationAgent", detail: "Prepares citations and workflow trace" }
];

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [workflow, setWorkflow] = useState(initialWorkflow);
  const [confidence, setConfidence] = useState("No answer yet");
  const [showWorkflow, setShowWorkflow] = useState(false);

  const status = loading ? "Retrieving" : "Ready";
  const hasAnswer = Boolean(answer);

  async function askQuestion() {
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setAnswer("Please enter a medical question first.");
      setConfidence("Low confidence");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query: cleanQuery })
      });
      const data = await response.json();
      setAnswer(data.answer || unknownResponse);
      setSources(data.sources || []);
      setWorkflow(data.workflow && data.workflow.length ? data.workflow : initialWorkflow);
      setConfidence(`${capitalize(data.confidence || "low")} confidence`);
    } catch (error) {
      setAnswer(unknownResponse);
      setSources([]);
      setConfidence("Low confidence");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      askQuestion();
    }
  }

  return h(
    "main",
    { className: "min-h-screen bg-[#0B1220] px-4 py-5 text-[#F8FAFC] sm:px-6 lg:px-8" },
    h(
      "div",
      { className: "mx-auto max-w-5xl" },
      h(Header, { status }),
      h(QuerySection, { query, setQuery, loading, askQuestion, handleKeyDown }),
      h(AnswerSection, { hasAnswer, answer, confidence, sources }),
      h(WorkflowSection, { workflow, showWorkflow, setShowWorkflow })
    )
  );
}

function Header({ status }) {
  return h(
    "header",
    { className: "rounded-lg border border-slate-800 bg-[#111827]/80 p-5 shadow-xl shadow-black/20" },
    h(
      "div",
      { className: "flex flex-wrap items-start justify-between gap-4" },
      h(
        "div",
        null,
        h("h1", { className: "text-2xl font-semibold tracking-normal text-[#F8FAFC] sm:text-3xl" }, "MedCite Sentinel"),
        h("p", { className: "mt-1 text-sm font-medium text-[#94A3B8]" }, "Trusted Medical Intelligence")
      ),
      h(
        "div",
        { className: "inline-flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1.5 text-sm font-semibold text-[#F8FAFC]" },
        h("span", { className: `h-2.5 w-2.5 rounded-full ${status === "Ready" ? "bg-[#14B8A6]" : "bg-[#94A3B8]"}` }),
        status
      )
    ),
    h(
      "div",
      { className: "mt-5 flex flex-wrap gap-x-3 gap-y-2 text-sm font-medium text-[#94A3B8]" },
      ["PubMed", "Nature", "BMJ", "Lancet", "AHA"].map((source, index) =>
        h(
          "span",
          { key: source, className: "inline-flex items-center gap-3" },
          source,
          index < 4 ? h("span", { className: "text-[#14B8A6]" }, "•") : null
        )
      )
    )
  );
}

function QuerySection({ query, setQuery, loading, askQuestion, handleKeyDown }) {
  return h(
    "section",
    { className: "mt-5 rounded-lg border border-slate-800 bg-[#111827]/80 p-5 shadow-xl shadow-black/20" },
    h("label", { htmlFor: "query", className: "text-sm font-semibold text-[#F8FAFC]" }, "Clinical Question"),
    h("textarea", {
      id: "query",
      rows: 6,
      spellCheck: true,
      value: query,
      onChange: (event) => setQuery(event.target.value),
      onKeyDown: handleKeyDown,
      placeholder: "Enter your medical question here...",
      className: "mt-3 min-h-40 w-full resize-y rounded-lg border border-slate-700 bg-[#0B1220] p-4 text-base leading-7 text-[#F8FAFC] outline-none placeholder:text-[#64748B] focus:border-[#14B8A6] focus:ring-4 focus:ring-[#14B8A6]/15"
    }),
    h(
      "div",
      { className: "mt-4 flex flex-col gap-3 sm:flex-row" },
      h(
        "button",
        {
          type: "button",
          disabled: loading,
          onClick: askQuestion,
          className: "min-h-11 rounded-lg bg-[#14B8A6] px-5 text-sm font-bold text-[#0B1220] transition hover:bg-[#2DD4BF] disabled:cursor-wait disabled:opacity-60"
        },
        loading ? "Retrieving Evidence..." : "Ask with Evidence"
      ),
      h(
        "button",
        {
          type: "button",
          onClick: () => setQuery(""),
          className: "min-h-11 rounded-lg border border-slate-700 px-5 text-sm font-bold text-[#F8FAFC] transition hover:border-[#14B8A6] hover:bg-[#14B8A6]/10"
        },
        "Clear"
      )
    ),
    h(
      "div",
      { className: "mt-5" },
      h("p", { className: "mb-2 text-sm font-semibold text-[#94A3B8]" }, "Examples:"),
      h(
        "div",
        { className: "flex flex-wrap gap-2" },
        examples.map(([label, value]) =>
          h(
            "button",
            {
              key: label,
              type: "button",
              onClick: () => setQuery(value),
              className: "rounded-full border border-slate-700 px-3 py-1.5 text-sm font-semibold text-[#94A3B8] transition hover:border-[#14B8A6] hover:text-[#F8FAFC]"
            },
            label
          )
        )
      )
    )
  );
}

function AnswerSection({ hasAnswer, answer, confidence, sources }) {
  return h(
    "section",
    { className: "mt-5 rounded-lg border border-slate-800 bg-[#111827]/80 p-5 shadow-xl shadow-black/20", "aria-live": "polite" },
    h(
      "div",
      { className: "flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4" },
      h("h2", { className: "text-lg font-semibold text-[#F8FAFC]" }, "Evidence Summary"),
      h("span", { className: "rounded-full border border-[#14B8A6]/40 bg-[#14B8A6]/10 px-3 py-1.5 text-sm font-semibold text-[#14B8A6]" }, confidence)
    ),
    h(
      "div",
      { className: "pt-4" },
      h(
        "p",
        { className: `whitespace-pre-line text-base leading-8 ${hasAnswer ? "text-[#F8FAFC]" : "text-[#94A3B8]"}` },
        hasAnswer ? answer : "Ask a question to see a grounded answer with citations."
      ),
      h(SourcesList, { sources })
    )
  );
}

function SourcesList({ sources }) {
  if (!sources.length) {
    return h("p", { className: "mt-5 text-sm text-[#94A3B8]" }, "Sources: No sources yet.");
  }

  return h(
    "div",
    { className: "mt-6" },
    h("h3", { className: "mb-3 text-sm font-semibold text-[#F8FAFC]" }, "Sources:"),
    h(
      "ul",
      { className: "grid gap-3" },
      sources.map((source, index) =>
        h(
          "li",
          { key: source.pmid || index, className: "rounded-lg border border-slate-800 bg-[#0B1220] p-4" },
          h(
            "a",
            { href: source.url, target: "_blank", rel: "noreferrer", className: "font-semibold text-[#F8FAFC] hover:text-[#14B8A6]" },
            `[${index + 1}] ${source.source || "PubMed"}`
          ),
          h("p", { className: "mt-1 text-sm leading-6 text-[#94A3B8]" }, source.title || "Untitled source"),
          h("p", { className: "mt-2 text-xs font-medium text-[#94A3B8]" }, `${source.journal || "Unknown journal"} ${source.year || ""}${source.pmid ? ` • PMID ${source.pmid}` : ""}`)
        )
      )
    )
  );
}

function WorkflowSection({ workflow, showWorkflow, setShowWorkflow }) {
  const rows = useMemo(() => workflow.length ? workflow : initialWorkflow, [workflow]);

  return h(
    "section",
    { className: "mt-5" },
    h(
      "button",
      {
        type: "button",
        onClick: () => setShowWorkflow(!showWorkflow),
        className: "inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-700 px-4 text-sm font-bold text-[#F8FAFC] transition hover:border-[#14B8A6] hover:bg-[#14B8A6]/10",
        "aria-expanded": showWorkflow
      },
      showWorkflow ? "Hide Workflow" : "View Workflow",
      h("span", { className: "text-[#14B8A6]" }, showWorkflow ? "▲" : "▼")
    ),
    showWorkflow
      ? h(
          "div",
          { className: "mt-4 rounded-lg border border-slate-800 bg-[#111827]/80 p-5 shadow-xl shadow-black/20" },
          h(
            "div",
            { className: "grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]" },
            h(
              "ol",
              { className: "grid list-decimal gap-3 pl-5" },
              rows.map((item, index) =>
                h(
                  "li",
                  { key: `${item.agent}-${index}`, className: "pl-2" },
                  h("strong", { className: "block text-sm font-semibold text-[#F8FAFC]" }, item.agent || "agent"),
                  h("span", { className: "block text-sm leading-6 text-[#94A3B8]" }, item.detail || item.status || "")
                )
              )
            ),
            h(
              "figure",
              { className: "overflow-hidden rounded-lg border border-slate-800 bg-[#0B1220]" },
              h("img", { src: "/docs/workflow-chart.svg", alt: "MedCite Sentinel agent workflow chart", className: "block h-auto w-full" })
            )
          )
        )
      : null
  );
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

ReactDOM.createRoot(document.getElementById("root")).render(h(App));
