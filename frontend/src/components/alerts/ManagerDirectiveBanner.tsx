interface Props { directive: string; }

export function ManagerDirectiveBanner({ directive }: Props) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded-lg">
      <span className="font-bold">L3 Override</span>
      <span>{directive}</span>
    </div>
  );
}
