interface Props {
  feedback: string;
}

export function SupervisorFeedbackBanner({ feedback }: Props) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded border text-xs bg-amber-400/5 border-amber-400/20 text-amber-200">
      <span className="flex-shrink-0 font-semibold text-amber-400 uppercase tracking-wide text-[10px] mt-0.5">
        Supervisor
      </span>
      <span className="text-neutral-300">{feedback}</span>
    </div>
  );
}
