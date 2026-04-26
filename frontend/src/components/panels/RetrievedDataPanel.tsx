import type { DbRecord, Observation } from "@/types";

interface Props { observation: Observation; }

function RecordCard({ kind, id, record }: { kind: "user" | "order"; id: string; record: DbRecord }) {
  const isNotFound = record === "not_found";
  const badge = kind === "user"
    ? "bg-cyan-50 border-cyan-200 text-cyan-700"
    : "bg-teal-50 border-teal-200 text-teal-700";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2 text-[11px]">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider font-semibold ${badge}`}>{kind}</span>
        <span className="font-mono text-gray-400 truncate" title={id}>{id}</span>
      </div>
      {isNotFound ? (
        <p className="font-mono text-amber-600">not_found</p>
      ) : (
        <div className="space-y-0.5">
          {Object.entries(record as Record<string, unknown>).slice(0, 8).map(([k, v]) => (
            <div key={k} className="flex gap-2 font-mono text-gray-600">
              <span className="text-gray-400">{k}:</span>
              <span className="truncate">{JSON.stringify(v)}</span>
            </div>
          ))}
          {Object.keys(record as Record<string, unknown>).length > 8 && (
            <p className="text-gray-400 italic">… {Object.keys(record as Record<string, unknown>).length - 8} more fields</p>
          )}
        </div>
      )}
    </div>
  );
}

export function RetrievedDataPanel({ observation }: Props) {
  const retrieved = observation.retrieved_data ?? { users: {}, orders: {} };
  const users = Object.entries(retrieved.users ?? {});
  const orders = Object.entries(retrieved.orders ?? {});

  if (users.length === 0 && orders.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">DB Lookups</span>
        <span className="text-[10px] text-gray-400 font-mono">{users.length + orders.length} record{users.length + orders.length === 1 ? "" : "s"}</span>
      </div>
      <div className="space-y-1.5">
        {users.map(([email, record]) => <RecordCard key={`u-${email}`} kind="user" id={email} record={record} />)}
        {orders.map(([oid, record]) => <RecordCard key={`o-${oid}`} kind="order" id={oid} record={record} />)}
      </div>
    </div>
  );
}
