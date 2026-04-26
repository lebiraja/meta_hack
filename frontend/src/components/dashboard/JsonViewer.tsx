"use client";

import { useState } from "react";

interface Props { data: unknown; title?: string; maxHeight?: number; }

function syntaxHighlight(json: string): string {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "text-indigo-600"; // number
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "text-gray-900 font-semibold" : "text-emerald-600"; // key : string
      } else if (/true|false/.test(match)) cls = "text-violet-600";
      else if (/null/.test(match)) cls = "text-gray-400";
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export function JsonViewer({ data, title, maxHeight = 400 }: Props) {
  const [copied, setCopied] = useState(false);
  const raw = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(raw).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        {title && <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">{title}</span>}
        <button onClick={handleCopy} className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors font-medium">
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div
        className="bg-gray-50 border border-gray-200 rounded-xl p-3 overflow-auto font-mono text-xs leading-relaxed"
        style={{ maxHeight }}
        dangerouslySetInnerHTML={{ __html: syntaxHighlight(raw) }}
      />
    </div>
  );
}
