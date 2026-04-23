"use client";

import { useState } from "react";

interface Props {
  data: unknown;
  title?: string;
  maxHeight?: number;
}

function syntaxHighlight(json: string): string {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "text-cyan-400"; // number
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = "text-indigo-300"; // key
        } else {
          cls = "text-green-400"; // string
        }
      } else if (/true|false/.test(match)) {
        cls = "text-amber-400";
      } else if (/null/.test(match)) {
        cls = "text-neutral-500";
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export function JsonViewer({ data, title, maxHeight = 400 }: Props) {
  const [copied, setCopied] = useState(false);

  if (data === null || data === undefined) {
    return (
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="px-3 py-2 bg-neutral-900 border-b border-neutral-800">
          <span className="text-xs text-neutral-500">{title ?? "JSON"}</span>
        </div>
        <div className="p-3 bg-neutral-950">
          <span className="text-xs text-neutral-600 font-mono">null</span>
        </div>
      </div>
    );
  }

  const json = JSON.stringify(data, null, 2);
  const highlighted = syntaxHighlight(json);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="border border-neutral-800 rounded overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-neutral-900 border-b border-neutral-800">
        <span className="text-xs text-neutral-500">{title ?? "JSON"}</span>
        <button
          onClick={handleCopy}
          className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors px-2 py-0.5 rounded hover:bg-neutral-800"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div
        className="overflow-auto p-3 bg-neutral-950"
        style={{ maxHeight }}
      >
        <pre
          className="text-xs font-mono leading-relaxed"
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      </div>
    </div>
  );
}
