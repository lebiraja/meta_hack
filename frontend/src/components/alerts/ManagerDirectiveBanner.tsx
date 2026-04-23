interface Props {
  directive: string;
}

export function ManagerDirectiveBanner({ directive }: Props) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded border text-xs bg-rose-400/5 border-rose-400/20 text-rose-200">
      <span className="flex-shrink-0 font-semibold text-rose-400 uppercase tracking-wide text-[10px] mt-0.5">
        Manager
      </span>
      <span className="text-neutral-300">{directive}</span>
    </div>
  );
}
