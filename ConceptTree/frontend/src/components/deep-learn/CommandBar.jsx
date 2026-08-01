import { useLanguage } from '../../contexts/LanguageContext';

export default function CommandBar({ commands, labels = {}, onCommand }) {
  const { t } = useLanguage();
  return (
    <div className="flex flex-wrap gap-2">
      {commands.map(cmd => (
        <button
          key={cmd}
          onClick={() => onCommand(cmd)}
          className="min-h-9 rounded-md border border-black/[0.1] bg-white px-4 py-1.5 text-sm font-medium text-zinc-700 transition-[background-color,border-color,transform] duration-150 hover:border-black/[0.18] hover:bg-[#f7f6f3] active:scale-[0.98]"
        >
          {labels[cmd] || t(`deep.command.${cmd}`) || cmd}
        </button>
      ))}
    </div>
  );
}
