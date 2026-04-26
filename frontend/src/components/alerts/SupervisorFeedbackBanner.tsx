interface Props { feedback: string; }

export function SupervisorFeedbackBanner({ feedback }: Props) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg">
      <span className="font-bold">L2 Feedback</span>
      <span>{feedback}</span>
    </div>
  );
}
