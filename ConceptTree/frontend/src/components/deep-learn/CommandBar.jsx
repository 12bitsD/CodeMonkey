const LABELS = {
  continue: '继续 →',
  expand: '展开',
  skip: '跳过',
  reteach: '重讲',
  confirm_test: '✅ 开始测试',
  not_ready: '再复习一下',
  restart: '🔄 重新开始',
};

export default function CommandBar({ commands, labels = {}, onCommand }) {
  return (
    <div className="flex flex-wrap gap-2">
      {commands.map(cmd => (
        <button
          key={cmd}
          onClick={() => onCommand(cmd)}
          className="px-3 py-1.5 rounded-lg text-sm border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors"
        >
          {labels[cmd] || LABELS[cmd] || cmd}
        </button>
      ))}
    </div>
  );
}
