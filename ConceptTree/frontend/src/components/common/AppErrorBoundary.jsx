import React from "react";
import { LanguageContext } from "../../contexts/LanguageContext";

export default class AppErrorBoundary extends React.Component {
  static contextType = LanguageContext;
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[AppErrorBoundary]", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.assign("/");
  };

  render() {
    const { t } = this.context;
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-canvas)] px-6 text-zinc-900">
        <div className="apple-card w-full max-w-md rounded-[28px] p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-400">
            {t("error.eyebrow")}
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-zinc-900">
            {t("error.title")}
          </h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            {t("error.help")}
          </p>
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={this.handleReload}
              className="flex-1 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700"
            >
              {t("error.reload")}
            </button>
            <button
              type="button"
              onClick={this.handleHome}
              className="flex-1 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-medium text-zinc-600 transition-colors hover:border-zinc-300 hover:text-zinc-900"
            >
              {t("error.home")}
            </button>
          </div>
        </div>
      </div>
    );
  }
}
