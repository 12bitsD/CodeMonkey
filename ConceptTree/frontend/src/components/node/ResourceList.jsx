import { ExternalLink } from "lucide-react";
import { useLanguage } from "../../contexts/LanguageContext";

export function ResourceList({ resources }) {
  const { t } = useLanguage();
  if (!resources?.length) return null;

  return (
    <section className="space-y-3">
      <h4 className="flex items-center gap-2 text-[0.65625rem] font-semibold uppercase leading-4 tracking-[0.075em] text-[#8f8e8b]">
        <ExternalLink size={12} strokeWidth={1.8} /> {t("node.resources")}
      </h4>
      <div className="space-y-2">
        {resources.map((resource, index) => (
          <a
            key={index}
            href={resource.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 rounded-xl bg-zinc-50 p-3 transition-colors hover:bg-zinc-100"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div className="truncate text-sm font-medium text-zinc-800">
                  {resource.name}
                </div>
                {resource.source === "web_search" && (
                  <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-medium text-teal-700">
                    {t("node.webSearch")}
                  </span>
                )}
              </div>
              {resource.reason && (
                <div className="mt-0.5 text-xs text-zinc-500">{resource.reason}</div>
              )}
            </div>
            <ExternalLink size={12} className="mt-1 flex-shrink-0 text-zinc-400" />
          </a>
        ))}
      </div>
    </section>
  );
}
